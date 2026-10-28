
import librosa
import numpy as np

from core.audio_analysis import AudioAnalyzer


class AudioService:
    def __init__(self, sample_rate=16000, chunk_duration=2.0):
        self.sample_rate = sample_rate
        self.analyzer = AudioAnalyzer(
            sample_rate=sample_rate,
            chunk_duration=chunk_duration
        )

    def process_audio_file(self, file_path):
        """Load audio from a supported audio file."""
        waveform, original_rate = librosa.load(
            file_path,
            sr=None,
            mono=True
        )

        waveform = self.analyzer.normalize_audio(
            waveform,
            original_rate=original_rate
        )

        return self.analyzer.segment_audio(waveform)

    def process_pcm_bytes(self, audio_bytes, original_rate=16000):
        """Process incoming 16-bit signed PCM audio bytes."""
        if not audio_bytes:
            return []

        # Each int16 sample occupies two bytes.
        if len(audio_bytes) % 2 != 0:
            raise ValueError("PCM byte length must be even")

        samples = np.frombuffer(audio_bytes, dtype="<i2")

        waveform = self.analyzer.normalize_audio(
            samples,
            original_rate=original_rate
        )

        return self.analyzer.segment_audio(waveform)

    def process_audio_array(self, waveform, original_rate=16000):
        """Process audio captured by a microphone or another source."""
        normalized = self.analyzer.normalize_audio(
            waveform,
            original_rate=original_rate
        )

        return self.analyzer.segment_audio(normalized)
