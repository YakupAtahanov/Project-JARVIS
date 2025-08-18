import ollama
from config import Config
from json import loads

class LLM:
    def __init__(self, system, release, version, machine, shell):
        self.llm_model = Config.LLM_MODEL
        self.chat_history = [
                    {
                        'role': 'system',
                        'content': Config.LLM_RULE.format(system=system, release=release, version=version, machine=machine, shell=shell),
                    }
                ]
        
        # Start preload
        ollama.chat(
            model=Config.LLM_MODEL,
            messages=self.chat_history
        )
    
    def ask(self, prompt):
        self.chat_history.append({
            'role': 'user',
            'content': prompt
        })

        response = ollama.chat(
            model=self.llm_model,
            messages=self.chat_history
        )["message"]["content"]

        return loads(response)