
import numpy as np


class AudioAnalyzer:
    def __init__(self, sample_rate=16000, frame_duration=0.025):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration)
        self.noise_floor = 0.005

    def analyze_audio_chunk(self, audio_data):
        """Extract energy, amplitude variation, and activity metrics."""
        audio = np.asarray(audio_data, dtype=np.float32).flatten()

        if audio.size == 0:
            return None

        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
        audio = np.clip(audio, -1.0, 1.0)

        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))
        dbfs = float(20 * np.log10(max(rms, 1e-10)))

        # Divide the signal into short frames.
        frame_rms = []
        zero_crossings = []

        for start in range(0, len(audio), self.frame_size):
            frame = audio[start:start + self.frame_size]

            if len(frame) == 0:
                continue

            frame_rms.append(float(np.sqrt(np.mean(frame ** 2))))

            crossings = np.count_nonzero(
                np.diff(np.signbit(frame))
            )
            zero_crossings.append(crossings / max(len(frame) - 1, 1))

        frame_rms = np.asarray(frame_rms, dtype=np.float32)
        zero_crossings = np.asarray(zero_crossings, dtype=np.float32)

        # Adaptive energy threshold for approximate activity detection.
        threshold = max(0.01, float(np.max(frame_rms)) * 0.15)
        active = frame_rms > threshold

        activity_ratio = float(np.mean(active)) if len(active) else 0.0

        # A rough low-percentile estimate, not calibrated noise measurement.
        estimated_noise = (
            float(np.percentile(frame_rms, 20))
            if len(frame_rms) else 0.0
        )

        return {
            "rms_amplitude": rms,
            "peak_amplitude": peak,
            "level_dbfs": dbfs,
            "amplitude_variation": float(np.std(frame_rms)),
            "zero_crossing_rate": (
                float(np.mean(zero_crossings))
                if len(zero_crossings) else 0.0
            ),
            "estimated_noise_floor": estimated_noise,
            "activity_ratio": activity_ratio,
            "estimated_active_seconds": (
                activity_ratio * len(audio) / self.sample_rate
            ),
            "duration_seconds": len(audio) / self.sample_rate
        }
