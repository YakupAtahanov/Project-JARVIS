from voice_input import SpeechToText
from config import Config
from voice_output import TextToSpeech
import os
import sounddevice as sd

tts = TextToSpeech(
    model_path="models/piper/en_US-libritts_r-medium.onnx",
    config_path="models/piper/en_US-libritts_r-medium.onnx.json",
)

stt = SpeechToText(
    model=Config.STT_MODEL, # tiny/base/small/medium/large
    english_only=True, # False for multilingual
    energy_threshold=1000,
    record_timeout=2.0,
    phrase_timeout=3.0,
    mic_name_substring=None
)
# def manager():
#     try:
#         stt.start()
#         print("Listening... Ctrl+C to stop.\n")
#         for text, is_final in stt.iter_results():
#             if is_final:
#                 print(text)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         stt.stop()

if __name__ == "__main__":
    pass
    # manager()