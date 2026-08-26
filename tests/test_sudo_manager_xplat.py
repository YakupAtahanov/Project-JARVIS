"""sudo management must degrade, not crash, where there is no euid (#174).

os.geteuid is POSIX-only. On Windows `jarvis sudo enable/disable` used to
raise AttributeError; there is no sudoers to manage there, so the correct
answer is a plain False. Simulated by hiding os.geteuid (the Windows shape)
so the check runs on any host.
"""

import os
from pathlib import Path

import pytest

from jarvis.core import sudo_manager


@pytest.fixture
def no_geteuid(monkeypatch):
    # Reproduce the Windows environment where os has no geteuid at all.
    monkeypatch.delattr(os, "geteuid", raising=False)


class TestSudoWithoutEuid:
    def test_enable_returns_false_not_crash(self, no_geteuid):
        assert sudo_manager.enable_sudo() is False

    def test_disable_returns_false_not_crash(self, no_geteuid):
        assert sudo_manager.disable_sudo() is False

    def test_status_is_readable_without_euid(self, no_geteuid):
        # Read-only status never needed euid; confirm it still answers.
        assert isinstance(sudo_manager.is_sudo_enabled(), bool)

    def test_status_survives_an_unreadable_sudoers_dir(self, monkeypatch):
        """/etc/sudoers.d is often 0750 root-only, so the existence check
        itself can be denied — `jarvis sudo` must report, not crash."""

        def denied(self):
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(Path, "exists", denied)
        assert sudo_manager.is_sudo_enabled() is False

    def test_non_root_euid_still_returns_false(self, monkeypatch):
        # With a real but non-zero euid, enable/disable still decline.
        monkeypatch.setattr(os, "geteuid", lambda: 1000, raising=False)
        assert sudo_manager.enable_sudo() is False
        assert sudo_manager.disable_sudo() is False
