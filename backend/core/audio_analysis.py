
import librosa
import numpy as np


class AudioAnalyzer:
    def __init__(self, sample_rate=16000, chunk_duration=2.0):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)

    def normalize_audio(self, audio_data, original_rate=None):
        """Convert audio into a mono float32 waveform."""
        audio = np.asarray(audio_data)

        if audio.size == 0:
            return np.array([], dtype=np.float32)

        # Convert stereo audio to mono when necessary.
        if audio.ndim == 2:
            if audio.shape[0] <= 2:
                audio = np.mean(audio, axis=0)
            else:
                audio = np.mean(audio, axis=1)

        audio = audio.astype(np.float32)

        # Convert 16-bit PCM values to the range [-1, 1].
        if np.issubdtype(np.asarray(audio_data).dtype, np.integer):
            audio /= 32768.0

        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
        audio = np.clip(audio, -1.0, 1.0)

        if original_rate and original_rate != self.sample_rate:
            audio = librosa.resample(
                audio,
                orig_sr=original_rate,
                target_sr=self.sample_rate
            )

        return audio.astype(np.float32)

    def analyze_audio_chunk(self, audio_data):
        """Calculate basic signal and activity measurements."""
        audio = np.asarray(audio_data, dtype=np.float32)

        if audio.size == 0:
            return None

        rms = float(np.sqrt(np.mean(np.square(audio))))
        peak_amplitude = float(np.max(np.abs(audio)))

        # Relative signal level; not calibrated microphone SPL.
        dbfs = float(20 * np.log10(max(rms, 1e-10)))

        # Simple energy-based activity estimate.
        frame_length = 400
        hop_length = 160

        rms_frames = librosa.feature.rms(
            y=audio,
            frame_length=frame_length,
            hop_length=hop_length
        )[0]

        # Adaptive threshold relative to this chunk's energy.
        threshold = max(0.01, float(np.max(rms_frames)) * 0.15)
        active_frames = int(np.sum(rms_frames > threshold))

        activity_ratio = (
            active_frames / len(rms_frames)
            if len(rms_frames) else 0.0
        )

        return {
            "rms_amplitude": rms,
            "peak_amplitude": peak_amplitude,
            "level_dbfs": dbfs,
            "activity_ratio": float(activity_ratio),
            "estimated_active_seconds": float(
                activity_ratio * len(audio) / self.sample_rate
            )
        }

    def segment_audio(self, audio, start_time=0.0):
        """Generate fixed-duration chunks with timestamps."""
        records = []

        for start in range(0, len(audio), self.chunk_size):
            chunk = audio[start:start + self.chunk_size]

            if len(chunk) == 0:
                continue

            chunk_start = start / self.sample_rate + start_time
            chunk_end = (
                start + len(chunk)
            ) / self.sample_rate + start_time

            metrics = self.analyze_audio_chunk(chunk)

            records.append({
                "start_seconds": round(chunk_start, 3),
                "end_seconds": round(chunk_end, 3),
                "sample_rate": self.sample_rate,
                "sample_count": len(chunk),
                "amplitude": chunk.tolist(),
                "metrics": metrics
            })

        return records
