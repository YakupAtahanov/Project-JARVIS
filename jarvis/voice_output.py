import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice
import time

class TextToSpeech:
    def __init__(self, model_path: str, config_path: str):
        self.tts = PiperVoice.load(model_path=model_path, config_path=config_path)
        self.device_index = sd.default.device[1]

    def say(self, text: str):
        sr = self.tts.config.sample_rate
        # RawOutputStream expects int16 PCM bytes
        with sd.RawOutputStream(samplerate=sr, channels=1, dtype="int16",
                                device=self.device_index, blocksize=0) as stream:
            for chunk in self.tts.synthesize(text):
                stream.write(chunk.audio_int16_bytes)
                time.sleep(0.4)