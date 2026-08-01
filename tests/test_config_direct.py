"""
Direct unit tests for jarvis.config module
"""

import os
from unittest.mock import patch

import pytest


@pytest.mark.config
class TestConfigDirect:
    """Direct test cases for Config class"""

    def test_config_import(self):
        """Test that config can be imported"""
        from jarvis.config import Config

        assert Config is not None

    @patch.dict(
        os.environ,
        {
            "TTS_MODEL_ONNX": "test.onnx",
            "TTS_MODEL_JSON": "test.json",
            "DISPATCH_TIMEOUT": "60",
        },
    )
    def test_config_values_from_env(self):
        """Test that config values are loaded from environment variables"""
        import importlib

        import jarvis.config

        importlib.reload(jarvis.config)
        Config = jarvis.config.Config

        assert Config.TTS_MODEL_ONNX == "test.onnx"
        assert Config.TTS_MODEL_JSON == "test.json"
        assert Config.DISPATCH_TIMEOUT == 60

    def test_llm_root_prompt_content(self):
        """Test LLM_ROOT_PROMPT contains action instructions"""
        from jarvis.config import Config

        assert '"action"' in Config.LLM_ROOT_PROMPT
        assert '"dispatch"' in Config.LLM_ROOT_PROMPT
        assert '"respond"' in Config.LLM_ROOT_PROMPT
        assert '"store"' in Config.LLM_ROOT_PROMPT
        assert '"recall"' in Config.LLM_ROOT_PROMPT
        assert '"search_memory"' in Config.LLM_ROOT_PROMPT

    def test_llm_wrong_json_format_message(self):
        """Test LLM_WRONG_JSON_FORMAT_MESSAGE content"""
        from jarvis.config import Config

        message = Config.LLM_WRONG_JSON_FORMAT_MESSAGE

        assert "JSON" in message
        assert "action" in message

    def test_llm_root_prompt_formatting(self):
        """Test LLM_ROOT_PROMPT formatting with system information"""
        from jarvis.config import Config

        system_info = {
            "system": "linux",
            "release": "5.4.0",
            "machine": "x86_64",
            "shell": ["bash", "-lc"],
            "data_consent_note": "Test consent note",
        }

        formatted = Config.LLM_ROOT_PROMPT.format(**system_info)

        assert "linux" in formatted
        assert "5.4.0" in formatted
        assert "x86_64" in formatted

    def test_default_values(self):
        """Test default values when environment variables are not set"""
        from jarvis.config import Config

        assert hasattr(Config, "TTS_MODEL_ONNX")
        assert hasattr(Config, "TTS_MODEL_JSON")
        assert hasattr(Config, "DISPATCH_BINARY")
        assert isinstance(Config.DISPATCH_TIMEOUT, int)
        assert Config.DISPATCH_TIMEOUT > 0


# ----------------------------------------------------------------------
# Interactive-job prompt guidance (#211)
# ----------------------------------------------------------------------


ROOT_TEMPLATES = (
    "LLM_ROOT_PROMPT",
    "LLM_ROOT_PROMPT_UNIFIED",
    "LLM_ROOT_PROMPT_NO_CONTEXTOR",
    "LLM_ROOT_PROMPT_UNIFIED_NO_CONTEXTOR",
)


@pytest.mark.config
class TestInteractiveJobPrompt:
    """ROOT drives interactive commands through the job model, not around them.

    The #199 rule taught the opposite — send the non-interactive form — which
    was true only while a shell command's stdin was closed. run_job gives the
    command a PTY that outlives the call, so the rule now teaches the loop.
    """

    @pytest.mark.parametrize("name", ROOT_TEMPLATES)
    def test_non_interactive_rule_is_gone(self, name):
        from jarvis.config import Config

        prompt = getattr(Config, name)

        assert "--noconfirm" not in prompt
        assert "non-interactive form" not in prompt

    @pytest.mark.parametrize("name", ROOT_TEMPLATES)
    def test_job_loop_is_taught(self, name):
        from jarvis.config import Config

        prompt = getattr(Config, name)

        assert "run_job" in prompt
        assert "execute_command" in prompt
        assert '"remind_after" on a run_job task' in prompt
        assert "send_input" in prompt
        assert "kill_job" in prompt

    @pytest.mark.parametrize("name", ROOT_TEMPLATES)
    def test_input_is_never_invented(self, name):
        from jarvis.config import Config

        prompt = getattr(Config, name)

        assert "EXACTLY what the output asked for" in prompt
        assert "never guess input the output did not ask for" in prompt

    @pytest.mark.parametrize("name", ROOT_TEMPLATES)
    def test_credentials_are_the_user_s_call(self, name):
        from jarvis.config import Config

        prompt = getattr(Config, name)

        assert "NEVER send a password or any other credential" in prompt
        assert "a password prompt is the user's decision" in prompt
