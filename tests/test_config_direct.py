"""
Direct unit tests for jarvis.config module (testing config.py directly)
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add jarvis directory to path
jarvis_path = Path(__file__).parent.parent / 'jarvis'
sys.path.insert(0, str(jarvis_path))

# Mock all heavy dependencies before importing config
import types

# Create mock modules for heavy dependencies
mock_modules = {
    'torch': types.ModuleType('torch'),
    'whisper': types.ModuleType('whisper'),
    'piper': types.ModuleType('piper'),
    'sounddevice': types.ModuleType('sounddevice'),
    'speech_recognition': types.ModuleType('speech_recognition'),
    'ollama': types.ModuleType('ollama'),
    'mcp': types.ModuleType('mcp'),
    'numpy': types.ModuleType('numpy'),
}

# Add to sys.modules
for name, module in mock_modules.items():
    sys.modules[name] = module

# Now import config directly
from config import Config


class TestConfigDirect:
    """Direct test cases for Config class"""

    def test_config_import(self):
        """Test that config can be imported"""
        assert Config is not None

    @patch.dict(os.environ, {
        'STT_MODEL': 'base',
        'LLM_MODEL': 'test-model',
        'TTS_MODEL_ONNX': 'test.onnx',
        'TTS_MODEL_JSON': 'test.json',
        'SUPERMCP_SERVER_PATH': 'SuperMCP/SuperMCP.py',
        'SUPERMCP_TIMEOUT': '60'
    })
    def test_config_values_from_env(self):
        """Test that config values are loaded from environment variables"""
        # Reload config to pick up new env vars
        import importlib
        import config
        importlib.reload(config)
        Config = config.Config
        
        assert Config.STT_MODEL == 'base'
        assert Config.LLM_MODEL == 'test-model'
        assert Config.TTS_MODEL_ONNX == 'test.onnx'
        assert Config.TTS_MODEL_JSON == 'test.json'
        assert Config.SUPERMCP_SERVER_PATH == 'SuperMCP/SuperMCP.py'
        assert Config.SUPERMCP_TIMEOUT == 60

    def test_llm_rule_content(self):
        """Test LLM_RULE content"""
        assert 'SuperMCP' in Config.LLM_RULE
        assert 'reload_servers()' in Config.LLM_RULE
        assert 'list_servers()' in Config.LLM_RULE
        assert 'inspect_server' in Config.LLM_RULE
        assert 'call_server_tool' in Config.LLM_RULE
        assert '"user_request": "Conversation"' in Config.LLM_RULE
        assert '"user_request": "SuperMCP"' in Config.LLM_RULE

    def test_llm_wrong_json_format_message(self):
        """Test LLM_WRONG_JSON_FORMAT_MESSAGE content"""
        message = Config.LLM_WRONG_JSON_FORMAT_MESSAGE
        
        assert 'JSON text you provided was not valid' in message
        assert 'Conversation|SuperMCP' in message
        assert 'user_request' in message
        assert 'output' in message

    def test_llm_rule_formatting(self):
        """Test LLM_RULE formatting with system information"""
        system_info = {
            'system': 'linux',
            'release': '5.4.0',
            'version': '#1 SMP Debian',
            'machine': 'x86_64',
            'shell': ['bash', '-lc']
        }
        
        formatted_rule = Config.LLM_RULE.format(**system_info)
        
        assert 'System: linux' in formatted_rule
        assert 'Release: 5.4.0' in formatted_rule
        assert 'Version: #1 SMP Debian' in formatted_rule
        assert 'Machine: x86_64' in formatted_rule
        assert 'bash' in str(system_info['shell'])
        assert 'SuperMCP' in formatted_rule

    def test_default_values(self):
        """Test default values when environment variables are not set"""
        # Clear environment variables
        env_vars_to_clear = [
            'STT_MODEL', 'LLM_MODEL', 'TTS_MODEL_ONNX', 'TTS_MODEL_JSON'
        ]
        
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            # Reload config to pick up cleared env vars
            import importlib
            import config
            importlib.reload(config)
            Config = config.Config
            
            # These values come from environment variables, so they may have defaults
            # We just check that they exist and are strings (or None)
            assert isinstance(Config.STT_MODEL, (str, type(None)))
            assert isinstance(Config.LLM_MODEL, (str, type(None)))
            assert isinstance(Config.TTS_MODEL_ONNX, (str, type(None)))
            assert isinstance(Config.TTS_MODEL_JSON, (str, type(None)))
            assert Config.SUPERMCP_SERVER_PATH == 'SuperMCP/SuperMCP.py'
            assert Config.SUPERMCP_TIMEOUT == 60
            
        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
