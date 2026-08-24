"""Tests for the xplat BasePlatform additions (Project-JARVIS #171/#173/#168/#169/#174).

ipc_verify_peer is exercised over a real socket for Linux (SO_PEERCRED) and
for the Windows interim token mechanism (pure Python, so it can run here
without an actual Windows box) — those are the parts with real runtime
behavior to check. macOS's LOCAL_PEERCRED path and the Windows named-pipe /
WinRT toast code cannot be exercised on Linux CI and are not covered here.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from jarvis.platform.linux import LinuxPlatform
from jarvis.platform.macos import MacOSPlatform, _applescript_quote
from jarvis.platform.windows import WindowsPlatform


class TestResolveSidecar:
    def test_config_override_wins_if_file_exists(self, tmp_path):
        p = LinuxPlatform()
        fake_binary = tmp_path / "dispatch"
        fake_binary.write_text("#!/bin/sh\n")
        fake_binary.chmod(0o755)
        assert p.resolve_sidecar("dispatch", str(fake_binary)) == str(fake_binary)

    def test_config_override_ignored_if_missing(self, tmp_path):
        p = LinuxPlatform()
        result = p.resolve_sidecar("ls", str(tmp_path / "nonexistent"))
        assert result is not None  # falls through to PATH and finds real `ls`

    def test_falls_back_to_search_dirs(self, tmp_path, monkeypatch):
        p = LinuxPlatform()
        monkeypatch.setattr(p, "sidecar_search_dirs", lambda: [tmp_path])
        monkeypatch.setattr("shutil.which", lambda name: None)
        target = tmp_path / "dispatch"
        target.write_text("#!/bin/sh\n")
        assert p.resolve_sidecar("dispatch") == str(target)

    def test_not_found_returns_none(self, tmp_path, monkeypatch):
        p = LinuxPlatform()
        monkeypatch.setattr(p, "sidecar_search_dirs", lambda: [tmp_path])
        monkeypatch.setattr("shutil.which", lambda name: None)
        assert p.resolve_sidecar("definitely-not-a-real-binary") is None


class TestSystemIpcCandidates:
    def test_linux_has_run_jarvis(self):
        assert LinuxPlatform().system_ipc_candidates() == ["/run/jarvis/input.sock"]

    def test_macos_and_windows_empty(self):
        assert MacOSPlatform().system_ipc_candidates() == []
        assert WindowsPlatform().system_ipc_candidates() == []


class TestLinuxIpcVerifyPeer:
    @pytest.mark.asyncio
    async def test_same_user_connection_accepted(self, tmp_path):
        p = LinuxPlatform()
        sock_path = str(tmp_path / "test.sock")
        results = []

        async def handler(reader, writer):
            results.append(await p.ipc_verify_peer(reader, writer))
            writer.close()

        server = await p.create_ipc_server(sock_path, handler)
        async with server:
            _, writer = await asyncio.open_unix_connection(sock_path)
            writer.close()
            await asyncio.sleep(0.1)
        p.ipc_cleanup(sock_path)

        assert results == [True]


class TestWindowsTokenAuth:
    @pytest.mark.asyncio
    async def test_client_via_ipc_connect_is_authenticated(self, tmp_path, monkeypatch):
        p = WindowsPlatform()
        monkeypatch.setattr(
            "jarvis.platform.windows._lock_down_to_current_user", lambda path: None
        )
        base_path = str(tmp_path / "input")
        seen = []

        async def handler(reader, writer):
            seen.append(await p.ipc_verify_peer(reader, writer))
            writer.close()

        server = await p.create_ipc_server(base_path, handler)
        async with server:
            sock = p.ipc_connect(base_path)
            await asyncio.sleep(0.1)
            sock.close()
        p.ipc_cleanup(base_path)

        assert seen == [True]

    @pytest.mark.asyncio
    async def test_connection_without_token_is_rejected(self, tmp_path, monkeypatch):
        p = WindowsPlatform()
        monkeypatch.setattr(
            "jarvis.platform.windows._lock_down_to_current_user", lambda path: None
        )
        base_path = str(tmp_path / "input")
        seen = []

        async def handler(reader, writer):
            seen.append(await p.ipc_verify_peer(reader, writer))
            writer.close()

        server = await p.create_ipc_server(base_path, handler)
        async with server:
            import socket

            port = server.sockets[0].getsockname()[1]
            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw.connect(("127.0.0.1", port))
            raw.sendall(b"not-the-real-token\n")
            await asyncio.sleep(0.1)
            raw.close()
        p.ipc_cleanup(base_path)

        assert seen == [False]


class TestApplescriptQuote:
    def test_escapes_quotes_and_backslashes(self):
        assert _applescript_quote('he said "hi"') == 'he said \\"hi\\"'
        assert _applescript_quote("back\\slash") == "back\\\\slash"


class TestModelsDirNotCwdRelative:
    def test_models_dir_is_absolute(self, monkeypatch):
        monkeypatch.delenv("MODELS_DIR", raising=False)
        monkeypatch.delenv("JARVIS_MODELS_DIR", raising=False)
        import importlib

        import jarvis.config as config_module

        importlib.reload(config_module)
        assert os.path.isabs(config_module.Config.MODELS_DIR)


class TestNotificationKillSwitch:
    """JARVIS_DISABLE_NOTIFICATIONS beats backend detection on every platform (#174)."""

    PLATFORMS = [LinuxPlatform, MacOSPlatform, WindowsPlatform]

    @pytest.mark.parametrize("platform_cls", PLATFORMS)
    def test_env_set_disables_even_with_backend_present(
        self, platform_cls, monkeypatch
    ):
        p = platform_cls()
        monkeypatch.setattr(p, "_detect_desktop_notifications", lambda: True)
        monkeypatch.setenv("JARVIS_DISABLE_NOTIFICATIONS", "1")
        assert p.has_desktop_notifications() is False

    @pytest.mark.parametrize("platform_cls", PLATFORMS)
    def test_env_absent_falls_through_to_detection(self, platform_cls, monkeypatch):
        p = platform_cls()
        monkeypatch.setattr(p, "_detect_desktop_notifications", lambda: True)
        monkeypatch.delenv("JARVIS_DISABLE_NOTIFICATIONS", raising=False)
        assert p.has_desktop_notifications() is True


class TestWindowsMultiSocketToken:
    """`platform.current` is a singleton and the daemon opens three endpoints
    (input, output, GUI). A per-call token overwrote its predecessor, so only
    the last-created socket authenticated and `jarvis send`/`jarvis confirm`
    were rejected on Windows (#174 Phase 3).

    Runs on any OS: the Windows backend is pure Python TCP plus files.
    """

    @staticmethod
    def _endpoints(tmp_path):
        return [
            str(tmp_path / name)
            for name in ("input.sock", "output.sock", "jarvis.sock")
        ]

    def _serve_all(self, tmp_path):
        p = WindowsPlatform()

        async def handler(reader, writer):
            pass

        async def build():
            servers = []
            for path in self._endpoints(tmp_path):
                servers.append(await p.create_ipc_server(path, handler))
            return servers

        servers = asyncio.run(build())
        for s in servers:
            s.close()
        return p

    def test_every_endpoint_publishes_the_verifiable_token(self, tmp_path):
        p = self._serve_all(tmp_path)
        for path in self._endpoints(tmp_path):
            published = (
                (tmp_path / (os.path.basename(path) + ".token")).read_text().strip()
            )
            assert (
                published == p._startup_token
            ), f"{os.path.basename(path)} published a token the daemon will reject"

    def test_closing_one_endpoint_does_not_lock_out_the_others(self, tmp_path):
        p = self._serve_all(tmp_path)
        paths = self._endpoints(tmp_path)
        p.ipc_cleanup(paths[0])
        assert (
            p._startup_token is not None
        ), "the surviving sockets can still be reached"
        p.ipc_cleanup(paths[1])
        assert p._startup_token is not None
        p.ipc_cleanup(paths[2])
        assert p._startup_token is None, "the last endpoint gone: forget the secret"
