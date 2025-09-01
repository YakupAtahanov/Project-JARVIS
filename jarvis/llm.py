import ollama
from config import Config
import json

class LLM:
    def __init__(self, system, release, version, machine, shell):
        self.llm_model = Config.LLM_MODEL
        self.default_chat = [
                    {
                        'role': 'system',
                        'content': Config.LLM_RULE.format(system=system, release=release, version=version, machine=machine, shell=shell),
                    }
                ]
        self.chat_history = list.copy(self.default_chat)

        print("LLM: Initiating Preload...")
        # Start preload
        ollama.chat(
            model=Config.LLM_MODEL,
            messages=self.chat_history
        )
        print("LLM: Initiation Complete!")
    
    def ask(self, prompt):
        self.chat_history.append({
            'role': 'user',
            'content': prompt
        })

        response = ollama.chat(
            model=self.llm_model,
            messages=self.chat_history
        )["message"]["content"]

        print(f"LLM Responded:'\n{response}\n----------")

        try:
            return json.loads(response)
        
        except json.decoder.JSONDecodeError:
            return self.ask("The JSON text you provided")
        
    def reset_history(self):
        self.chat_history = list.copy(self.default_chat)
