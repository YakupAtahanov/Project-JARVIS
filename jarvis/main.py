from .voice_input import SpeechToText
from .config import Config
from .voice_output import TextToSpeech
from .llm import LLM
from .supermcp_client import SuperMCPWrapper
from .voice_activation import VoiceActivation
from json import dumps
import platform
import shutil
import time

class Jarvis:
    def __init__(self, text_mode=False):
        """
        Initialize JARVIS AI Assistant
        
        Args:
            text_mode: If True, skip voice input components (STT, Voice Activation)
                      for CLI text-only mode
        """
        self.text_mode = text_mode
        
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

        # Only initialize voice input components if not in text mode
        if not text_mode:
            print("Initiating STT...")
            self.stt = SpeechToText(
                model_path=Config.VOSK_MODEL_PATH,  # Vosk model path
                sample_rate=16000,
                chunk_size=4000,
                phrase_timeout=3.0,
                silence_timeout=1.0,
                device_index=None  # Use default audio device
            )

            print("Initiating Voice Activation...")
            self.voice_activation = VoiceActivation(
                wake_words=Config.WAKE_WORDS,
                model_path=Config.VOSK_MODEL_PATH,
                sample_rate=16000,
                chunk_size=4000,
                sensitivity=Config.VOICE_ACTIVATION_SENSITIVITY,
                on_wake_word=self._on_wake_word_detected
            )
            
            # Flag to indicate wake word was detected
            self._wake_word_detected = False
        else:
            # Set placeholders for text mode
            self.stt = None
            self.voice_activation = None
            self._wake_word_detected = False
            
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
        
        # Handle output based on configured mode
        if Config.OUTPUT_MODE == "voice":
            self.tts.say(response["output"])
        elif Config.OUTPUT_MODE == "text":
            print(response["output"])
        
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

    def _on_wake_word_detected(self):
        """Callback when wake word is detected."""
        print("Wake word detected! Setting flag...")
        # Just set a flag - don't try to stop the thread from within itself
        self._wake_word_detected = True

    def listen_with_activation(self):
        """Listen with voice activation (wake word detection)."""
        try:
            print("Starting JARVIS with voice activation...")
            print("Say 'Jarvis' to activate me!")
            print("Press Ctrl+C to stop.\n")
            
            # Start voice activation
            if not self.voice_activation.start_listening():
                print("Failed to start voice activation")
                return
            
            # Main loop - check for wake word detection
            while True:
                if self._wake_word_detected:
                    self._wake_word_detected = False  # Reset flag
                    self._process_voice_command()
                time.sleep(0.5)  # Small delay to avoid busy waiting
                    
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.voice_activation.cleanup()
    
    def _process_voice_command(self):
        """Process voice command after wake word detection."""
        print("Starting voice processing...")
        
        # Stop voice activation to free up audio resources
        self.voice_activation.stop_listening()
        
        # Give a brief response
        self.tts.say("Yes, I'm listening.")
        
        # Start STT processing
        self.stt.start()
        try:
            print("Listening for your command...")
            for text, is_final in self.stt.iter_results():
                if is_final and text.strip():
                    print(f"Final Input: {text}")
                    response = self.ask(prompt=text)
                    print(f"Response: {response['output']}")
                    break  # Exit after processing one command
        except Exception as e:
            print(f"Error processing voice command: {e}")
        finally:
            self.stt.stop()
            print("Voice processing completed. Restarting wake word detection...")
            
            # Restart voice activation
            if not self.voice_activation.start_listening():
                print("Failed to restart voice activation")

    def listen(self):
        """Legacy continuous listening mode (without wake word detection)."""
        try:
            self.stt.start()
            self.tts.say("I am listenning.")
            print("Listening... Ctrl+C to stop.\n")
            for text, is_final in self.stt.iter_results():
                if is_final:
                    print(text)
                    self.ask(prompt=text)  # ask() now handles output based on OUTPUT_MODE
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.stt.stop()

def main():
    """Main entry point for JARVIS - delegates to CLI handler"""
    from .cli import main as cli_main
    cli_main()

if __name__ == "__main__":
    main()
