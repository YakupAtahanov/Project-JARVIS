"""_dmcp_base_dir() per-OS fallback resolution (jarvis/dispatch/dmcp_registry.py).

dmcp writes under ``<data_local>/mcp`` on every OS (the ``dirs`` crate joining
the literal ``"mcp"``). When ``dmcp paths --json`` is unavailable the hardcoded
fallback must still land in ``mcp`` — the old fallback pointed macOS at
``.../dmcp`` and Windows at ``.../dmcp/data``, silently missing the real data
dir on both.
"""

import sys

import pytest

from jarvis.dispatch import dmcp_registry


def _force_paths_command_unavailable(monkeypatch):
    def _boom(*args, **kwargs):
        raise FileNotFoundError("dmcp not on PATH")

    monkeypatch.setattr(dmcp_registry.subprocess, "run", _boom)


@pytest.mark.unit
class TestDmcpBaseDirFallback:
    def test_win32_fallback_ends_in_mcp(self, monkeypatch):
        _force_paths_command_unavailable(monkeypatch)
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\test\\AppData\\Local")

        result = dmcp_registry._dmcp_base_dir()

        assert result.name == "mcp"
        assert "dmcp" not in result.parts

    def test_darwin_fallback_ends_in_mcp(self, monkeypatch):
        _force_paths_command_unavailable(monkeypatch)
        monkeypatch.setattr(sys, "platform", "darwin")

        result = dmcp_registry._dmcp_base_dir()

        assert result.name == "mcp"
        assert "dmcp" not in result.parts

    def test_linux_fallback_still_ends_in_mcp(self, monkeypatch, tmp_path):
        _force_paths_command_unavailable(monkeypatch)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

        result = dmcp_registry._dmcp_base_dir()

        assert result == tmp_path / "mcp"
