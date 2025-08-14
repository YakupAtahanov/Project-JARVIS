from typing import Optional

class PiperEngine():
    """
    Requires:
      pip install piper-tts sounddevice soundfile numpy
    And a voice model file (e.g., 'en_US-amy-low.onnx').
    """
    def __init__(self, model_path: str, device_index: Optional[int] = None):
        import numpy as np
        import sounddevice as sd
        import soundfile as sf
        import piper

        self._np = np
        self._sd = sd
        self._sf = sf
        self._piper = piper
        # Load Piper model once
        self.tts = piper.PiperVoice(model_path)

        # Choose audio output device (None = default)
        self.device_index = device_index

    def say(self, text: str):
        # Generate PCM samples (16-bit) at model sample rate
        wav_bytes = self.tts.synthesize(text)
        # Decode WAV bytes to ndarray + samplerate
        import io
        with io.BytesIO(wav_bytes) as bio:
            data, sr = self._sf.read(bio, dtype="int16")
        # Play
        self._sd.play(data, sr, device=self.device_index, blocking=True)