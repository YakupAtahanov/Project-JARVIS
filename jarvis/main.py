from voice_input import SpeechToText
from config import Config
from voice_output import TextToSpeech
from llm import LLM
from supermcp_client import SuperMCPWrapper
from json import dumps
import platform
import shutil

class Jarvis:
    def __init__(self):
        print("Getting system information...")
        system_info = self._get_system_info()
        print("Initiating SuperMCP...")
        self.supermcp = SuperMCPWrapper()
        print("Initiating LLM...")
        self.llm = LLM(
            system=system_info['system'],
            release=system_info['release'],
            version=system_info['version'],
            machine=system_info['machine'],
            shell=system_info['shell']
        )

        print("Initiating TTS...")
        self.tts = TextToSpeech(
            model_path=f"models/piper/{Config.TTS_MODEL_ONNX}",
            config_path=f"models/piper/{Config.TTS_MODEL_JSON}",
        )

        print("Initiating STT...")
        self.stt = SpeechToText(
            model=Config.STT_MODEL, # tiny/base/small/medium/large
            english_only=True, # False for multilingual
            energy_threshold=1000,
            record_timeout=2.0,
            phrase_timeout=3.0,
            mic_name_substring=None
        )
        print("Initiations Complete!")

    def _get_system_info(self):
        """Get system information for LLM initialization"""
        system = platform.system().lower()
        
        # Get shell command (same logic as TerminalManager)
        if system == "windows":
            if shutil.which("pwsh"):
                shell = ["pwsh", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]
            elif shutil.which("powershell"):
                shell = ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]
            else:
                shell = ["cmd.exe", "/d", "/s", "/c"]
        else:
            if shutil.which("bash"):
                shell = ["bash", "-lc"]
            else:
                shell = ["sh", "-lc"]
        
        return {
            'system': system,
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'shell': shell
        }

    def ask(self, prompt):
        response = self.llm.ask(prompt)
        while response['user_request'] != "Conversation":
            if response['user_request'] == "SuperMCP":
                # Handle SuperMCP commands
                supermcp_output = self._execute_supermcp_commands(response['output'])
                print(f"Output from SuperMCP:\n{supermcp_output}\n----------")
                response = self.llm.ask(dumps(supermcp_output))

        self.llm.reset_history()
        return response

    def _execute_supermcp_commands(self, command_sequence):
        """Execute a sequence of SuperMCP commands"""
        try:
            commands = [cmd.strip() for cmd in command_sequence.split(';') if cmd.strip()]
            results = []
            
            for command in commands:
                print(f"Executing SuperMCP command: {command}")
                result = self._parse_and_execute_command(command)
                results.append(result)
            
            return {"success": True, "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_and_execute_command(self, command):
        """Parse and execute a single SuperMCP command"""
        try:
            if command == "reload_servers()":
                return self.supermcp.reload_servers()
            elif command == "list_servers()":
                return self.supermcp.list_servers()
            elif command.startswith("inspect_server("):
                # Extract server name from inspect_server(server_name)
                server_name = command[16:-1]  # Remove "inspect_server(" and ")"
                return self.supermcp.inspect_server(server_name)
            elif command.startswith("call_server_tool("):
                # Parse call_server_tool(server_name, tool_name, {arguments})
                try:
                    # Simple parsing for call_server_tool - this is a basic implementation
                    # Extract the content between parentheses
                    content = command[17:-1]  # Remove "call_server_tool(" and ")"
                    
                    # Split by comma, but be careful with nested braces
                    parts = []
                    current_part = ""
                    brace_count = 0
                    
                    for char in content:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        elif char == ',' and brace_count == 0:
                            parts.append(current_part.strip())
                            current_part = ""
                            continue
                        current_part += char
                    
                    if current_part:
                        parts.append(current_part.strip())
                    
                    if len(parts) >= 3:
                        server_name = parts[0]
                        tool_name = parts[1]
                        # For now, pass empty arguments - we can enhance this later
                        return self.supermcp.call_server_tool(server_name, tool_name, {})
                    else:
                        return {"error": f"Invalid call_server_tool format: {command}"}
                except Exception as e:
                    return {"error": f"Failed to parse call_server_tool: {e}"}
            else:
                return {"error": f"Unknown command: {command}"}
        except Exception as e:
            return {"error": f"Command execution failed: {e}"}

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
