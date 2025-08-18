from voice_input import SpeechToText
from config import Config
from voice_output import TextToSpeech
from terminal_manager import TerminalManager
from llm import LLM
from json import dumps

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

        self.tts = TextToSpeech(
            model_path="models/piper/en_US-libritts_r-medium.onnx",
            config_path="models/piper/en_US-libritts_r-medium.onnx.json",
        )

        self.stt = SpeechToText(
            model=Config.STT_MODEL, # tiny/base/small/medium/large
            english_only=True, # False for multilingual
            energy_threshold=1000,
            record_timeout=2.0,
            phrase_timeout=3.0,
            mic_name_substring=None
        )

    def ask(self, prompt):
        response = self.llm.ask(prompt)
        while response['user_request'] != "Conversation":
            if response['user_request'] == "Command":
                terminal_output = self.tm.run_command(response['output'])
                print(f"Output from terminal:\n{terminal_output}\n----------")
                response = self.llm.ask(dumps(terminal_output))

        return response

    def listen(self):
        try:
            self.stt.start()
            self.tts.say("I am listenning.")
            print("Listening... Ctrl+C to stop.\n")
            for text, is_final in self.stt.iter_results():
                if is_final:
                    print(text)
                    self.tts.say(self.ask(prompt=text)["output"])
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.stt.stop()

if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.listen()