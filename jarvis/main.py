# app.py
from voice_input import SpeechToText

stt = SpeechToText(
    model="small", # tiny/base/small/medium/large
    english_only=True, # False for multilingual
    energy_threshold=1000,
    record_timeout=2.0,
    phrase_timeout=3.0,
    mic_name_substring=None
)

try:
    stt.start()
    print("Listening... Ctrl+C to stop.\n")
    for text, is_final in stt.iter_results():
        if is_final:
            print(text)
            
except KeyboardInterrupt:
    pass
finally:
    stt.stop()
