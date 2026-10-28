
import numpy as np
from core.audio_analysis import AudioAnalyzer


class AudioService:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.analyzer = AudioAnalyzer(sample_rate=sample_rate)

    def process_pcm_bytes(self, audio_bytes, original_rate=16000):
        if not audio_bytes:
            return None

        if len(audio_bytes) % 2:
            raise ValueError("Expected 16-bit PCM audio bytes")

        samples = np.frombuffer(audio_bytes, dtype="<i2")
        waveform = samples.astype(np.float32) / 32768.0

        if original_rate != self.sample_rate:
            raise ValueError(
                "Audio sample rate must match the configured service rate"
            )

        return self.analyzer.analyze_audio_chunk(waveform)
