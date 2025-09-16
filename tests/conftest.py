"""
Test configuration and fixtures for JARVIS
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""STT_MODEL=base
LLM_MODEL=test-model
TTS_MODEL_ONNX=test.onnx
TTS_MODEL_JSON=test.json
SUPERMCP_SERVER_PATH=SuperMCP/SuperMCP.py
SUPERMCP_TIMEOUT=30
""")
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        'STT_MODEL': 'base',
        'LLM_MODEL': 'test-model',
        'TTS_MODEL_ONNX': 'test.onnx',
        'TTS_MODEL_JSON': 'test.json',
        'SUPERMCP_SERVER_PATH': 'SuperMCP/SuperMCP.py',
        'SUPERMCP_TIMEOUT': 30
    }


@pytest.fixture
def mock_system_info():
    """Mock system information"""
    return {
        'system': 'linux',
        'release': '5.4.0',
        'version': '#1 SMP Debian',
        'machine': 'x86_64',
        'shell': ['bash', '-lc']
    }


# Additional fixtures can be added here as needed for future tests
