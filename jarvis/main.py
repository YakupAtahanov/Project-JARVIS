from voice_input import SpeechToText
from config import Config
from voice_output import TextToSpeech
import os
import sounddevice as sd
from terminal_manager import TerminalManager
from llm import LLM

class Jarvis:
    def __init__(self):
        self.tm = TerminalManager()
        self.llm = LLM(
            system=self.tm.system,
            release=self.tm.release,
            version=self.tm.version,
            machine=self.tm.machine,
            shell=self.tm.shell
        )

        # self.tts = TextToSpeech(
        #     model_path="models/piper/en_US-libritts_r-medium.onnx",
        #     config_path="models/piper/en_US-libritts_r-medium.onnx.json",
        # )

        # self.stt = SpeechToText(
        #     model=Config.STT_MODEL, # tiny/base/small/medium/large
        #     english_only=True, # False for multilingual
        #     energy_threshold=1000,
        #     record_timeout=2.0,
        #     phrase_timeout=3.0,
        #     mic_name_substring=None
        # )

    def ask(self, prompt):
        pass

    # def listen():
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

tm = TerminalManager()
llm = LLM(system=tm.system, release=tm.release, version=tm.version, machine=tm.machine, shell=tm.shell)

if __name__ == "__main__":
    print(type(llm.ask("Upgrade my pip")))
    # print(tm.run_command("pip install --upgrade pip"))
    # manager()