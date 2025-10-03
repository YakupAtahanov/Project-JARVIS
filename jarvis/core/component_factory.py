""from typing import Optional
from ..config import Config
from ..voice_output import TextToSpeech
from ..llm import LLM
from ..supermcp_client import SuperMCPWrapper
from .system_info import SystemInfo
from .command_parser import SuperMCPCommandParser
from .output_manager import OutputManager
from .voice_manager import VoiceManager


class ComponentFactory:
    @staticmethod
    def create_llm() -> LLM:
        print("Getting system information...")
        system_info = SystemInfo.get_system_info()
        
        print("Initiating LLM...")
        return LLM(
            system=system_info['system'],
            release=system_info['release'],
            version=system_info['version'],
            machine=system_info['machine'],
            shell=system_info['shell']
        )
    
    @staticmethod
    def create_tts() -> TextToSpeech:
        print("Initiating TTS...")
        return TextToSpeech(
            model_path=f"models/piper/{Config.TTS_MODEL_ONNX}",
            config_path=f"models/piper/{Config.TTS_MODEL_JSON}",
        )
    
    @staticmethod
    def create_supermcp() -> SuperMCPWrapper:
        print("Initiating SuperMCP...")
        return SuperMCPWrapper()
    
    @staticmethod
    def create_command_parser(supermcp: SuperMCPWrapper) -> SuperMCPCommandParser:
        return SuperMCPCommandParser(supermcp)
    
    @staticmethod
    def create_output_manager(tts: TextToSpeech) -> OutputManager:
        return OutputManager(tts)
    
    @staticmethod
    def create_voice_manager(on_command) -> Optional[VoiceManager]:
        print("Initiating Voice Activation...")
        return VoiceManager(on_command)
    
    @staticmethod
    def create_all_components(text_mode: bool = False, on_voice_command=None):
        """
        Create all JARVIS components

        Args:
            text_mode: If True, skip voice components
            on_voice_command: Callback for voice commands

        Returns:
            Dictionary of all initialized components
        """
        components = {}
        
        # Core components (always needed)
        components['llm'] = ComponentFactory.create_llm()
        components['tts'] = ComponentFactory.create_tts()
        components['supermcp'] = ComponentFactory.create_supermcp()
        
        # Dependent components
        components['command_parser'] = ComponentFactory.create_command_parser(
            components['supermcp']
        )
        components['output_manager'] = ComponentFactory.create_output_manager(
            components['tts']
        )
        
        # Voice components (only if not in text mode)
        if not text_mode and on_voice_command:
            components['voice_manager'] = ComponentFactory.create_voice_manager(
                on_voice_command
            )
        
        print("Initiations Complete!")
        return components
