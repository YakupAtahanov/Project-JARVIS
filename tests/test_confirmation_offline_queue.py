"""#224 follow-up — ``jarvis confirm`` must work while the daemon is OFF.

The socket-only CLI exited 1 the moment the endpoint was missing, so a review
queue that now survives a restart was still unreviewable between restarts.
Offline, the CLI reads the persisted store directly and appends decisions to
``$JARVIS_DATA_DIR/confirmation_decisions.json``; the daemon replays them at
startup through the same injection a live socket client triggers.
"""

import asyncio
import json
import logging
from unittest.mock import MagicMock, Mock

import pytest

import jarvis.cli as cli
from jarvis.core import confirmation_manager as cm
from jarvis.core.confirmation_manager import ConfirmationManager
from jarvis.dispatch.goal_manager import GoalManager
from jarvis.runtime import lifecycle, root_handlers
from tests.test_confirmation_persistence import _detail, _FakeApp, _request, _task

_LOG = logging.getLogger("test")

_OFFLINE_NOTICE = "daemon offline — decisions queue and apply at next start"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point every JARVIS_DATA_DIR derivation at a scratch directory."""
    monkeypatch.setattr(cm.Config, "JARVIS_DATA_DIR", str(tmp_path))
    return tmp_path


def _seed_store(data_dir, request_id="abc123", details=None, session_id="goal-1"):
    """Write a real store file the way a live daemon would."""
    mgr = ConfirmationManager(store_path=str(data_dir / "confirmations.json"))
    mgr.set_event_injector(Mock())
    asyncio.run(_request(mgr, request_id, details=details, session_id=session_id))
    return mgr


def _queue_file(data_dir):
    return data_dir / "confirmation_decisions.json"


def _read_queue(data_dir):
    return json.loads(_queue_file(data_dir).read_text(encoding="utf-8"))


def _run_confirm(monkeypatch, argv, endpoint=None, connect_error=None, ack=None):
    """Drive ``jarvis confirm`` with the daemon reachable or not."""
    monkeypatch.setattr(cli.sys, "argv", argv)
    monkeypatch.setattr(cli, "_find_ipc_endpoint", lambda quiet=False: endpoint)

    sent = {}
    if endpoint:
        import jarvis.platform as platform_pkg

        if connect_error is not None:

            def _connect(path):
                raise connect_error

        else:
            sock = MagicMock()
            sock.sendall.side_effect = lambda data: sent.update(
                request=json.loads(data.decode("utf-8"))
            )
            sock.makefile.return_value.readline.return_value = json.dumps(
                ack or {"type": "ack", "message": "ok"}
            )

            def _connect(path):
                return sock

        monkeypatch.setattr(platform_pkg.current, "ipc_connect", _connect)

    cli._cmd_confirm()
    return sent


@pytest.mark.unit
class TestOfflineList:
    def test_renders_store_entries_when_endpoint_is_absent(
        self, data_dir, monkeypatch, capsys
    ):
        mgr = _seed_store(data_dir)
        expected_line = mgr.list_pending()[0]["tool_lines"][0]

        _run_confirm(monkeypatch, ["jarvis", "confirm"])

        out = capsys.readouterr().out
        assert "Pending confirmations (1):" in out
        assert "[abc123]" in out
        assert "(session goal-1," in out
        assert f"        [0] {expected_line}" in out
        assert _OFFLINE_NOTICE in out

    def test_renders_store_entries_when_connect_is_refused(
        self, data_dir, monkeypatch, capsys
    ):
        _seed_store(data_dir)

        _run_confirm(
            monkeypatch,
            ["jarvis", "confirm"],
            endpoint="/fake/sock",
            connect_error=ConnectionRefusedError("refused"),
        )

        out = capsys.readouterr().out
        assert "[abc123]" in out
        assert _OFFLINE_NOTICE in out

    def test_failed_ownership_check_is_loud_but_still_reviewable(
        self, data_dir, monkeypatch, capsys
    ):
        """A socket that is not ours is a security signal, not a stopped daemon
        — say so, then fall back, since the queue is our own file either way."""
        import jarvis.platform as platform_pkg

        _seed_store(data_dir)
        monkeypatch.setattr(cli.sys, "argv", ["jarvis", "confirm"])
        monkeypatch.setattr(cli.Config, "JARVIS_INPUT_SOCKET", "/fake/sock")
        monkeypatch.setattr(cli, "_ipc_endpoint_exists", lambda p: True)
        monkeypatch.setattr(platform_pkg.current, "ipc_verify_owner", lambda p: False)

        cli._cmd_confirm()

        out = capsys.readouterr().out
        assert "ownership check failed" in out
        assert "[abc123]" in out
        assert _OFFLINE_NOTICE in out

    def test_empty_store_says_nothing_pending(self, data_dir, monkeypatch, capsys):
        _run_confirm(monkeypatch, ["jarvis", "confirm"])

        out = capsys.readouterr().out
        assert "No pending confirmations." in out
        assert _OFFLINE_NOTICE in out

    def test_lists_already_queued_decisions(self, data_dir, monkeypatch, capsys):
        _seed_store(data_dir)
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "abc123", "0"])
        capsys.readouterr()

        _run_confirm(monkeypatch, ["jarvis", "confirm"])

        out = capsys.readouterr().out
        assert "Queued decisions (1)" in out
        assert "[abc123] approve items 0" in out


@pytest.mark.unit
class TestOfflineDecide:
    def test_approve_queues_the_socket_protocol_shape(
        self, data_dir, monkeypatch, capsys
    ):
        _seed_store(data_dir)

        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "abc123"])

        assert _read_queue(data_dir) == [
            {"type": "approve_confirmation", "id": "abc123"}
        ]
        out = capsys.readouterr().out
        assert "abc123" in out
        assert "applies when the daemon starts" in out

    def test_deny_queues_the_socket_protocol_shape(self, data_dir, monkeypatch):
        _seed_store(data_dir)

        _run_confirm(monkeypatch, ["jarvis", "confirm", "deny", "abc123"])

        assert _read_queue(data_dir) == [{"type": "deny_confirmation", "id": "abc123"}]

    def test_partial_approve_queues_approved_indices(self, data_dir, monkeypatch):
        details = [_detail("sys.execute_command", "pacman"), _detail("fs.delete", "rm")]
        _seed_store(data_dir, "batch", details=details)

        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "batch", "0"])

        assert _read_queue(data_dir) == [
            {
                "type": "partial_approve_confirmation",
                "id": "batch",
                "approved_indices": [0],
            }
        ]

    def test_approve_all_queues_the_socket_protocol_shape(self, data_dir, monkeypatch):
        _seed_store(data_dir)

        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve-all"])

        assert _read_queue(data_dir) == [{"type": "approve_all_confirmations"}]

    def test_repeated_decision_replaces_the_earlier_one(self, data_dir, monkeypatch):
        _seed_store(data_dir)
        _seed_store(data_dir, "other")

        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "abc123"])
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "other"])
        _run_confirm(monkeypatch, ["jarvis", "confirm", "deny", "abc123"])

        assert _read_queue(data_dir) == [
            {"type": "approve_confirmation", "id": "other"},
            {"type": "deny_confirmation", "id": "abc123"},
        ]

    def test_unknown_id_errors_and_writes_nothing(self, data_dir, monkeypatch, capsys):
        _seed_store(data_dir)

        with pytest.raises(SystemExit) as exc:
            _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "nope"])

        assert exc.value.code == 1
        assert not _queue_file(data_dir).exists()
        assert "nope" in capsys.readouterr().out

    def test_approve_all_with_empty_store_writes_nothing(
        self, data_dir, monkeypatch, capsys
    ):
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve-all"])

        assert not _queue_file(data_dir).exists()
        assert "nothing pending" in capsys.readouterr().out.lower()


@pytest.mark.unit
class TestLiveDaemonPreference:
    def test_reachable_daemon_queues_nothing(self, data_dir, monkeypatch):
        _seed_store(data_dir)

        sent = _run_confirm(
            monkeypatch,
            ["jarvis", "confirm", "approve", "abc123"],
            endpoint="/fake/sock",
        )

        assert sent["request"] == {"type": "approve_confirmation", "id": "abc123"}
        assert not _queue_file(data_dir).exists()


class _FakeEvents:
    """Stands in for the EventMerger's thread-safe injection surface."""

    def __init__(self):
        self.injected = []

    def inject_confirmation_response(self, data):
        self.injected.append(data)


class _QueueApp(_FakeApp):
    def __init__(self, goals, confirmation):
        super().__init__(goals, confirmation)
        self.events = _FakeEvents()


def _restarted_app(data_dir):
    """A fresh daemon: manager reloaded from the store, goal tree empty."""
    restarted = ConfirmationManager(store_path=str(data_dir / "confirmations.json"))
    return _QueueApp(GoalManager(archive_dir=str(data_dir)), restarted)


def _stub_root_llm(monkeypatch):
    monkeypatch.setattr(root_handlers, "build_root_context", lambda a, log, **k: "")
    monkeypatch.setattr(root_handlers, "emit_activity", lambda *a, **k: None)

    async def _fake_ask(a, log, c, **k):
        return {"action": "respond", "output": "ok"}

    monkeypatch.setattr(root_handlers, "ask_llm", _fake_ask)


@pytest.mark.unit
class TestStartupApply:
    def test_queued_approve_resumes_through_the_normal_path(
        self, data_dir, monkeypatch, caplog
    ):
        _seed_store(data_dir, "r1", session_id="goal-gone")
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "r1"])
        app = _restarted_app(data_dir)
        _stub_root_llm(monkeypatch)

        with caplog.at_level(logging.INFO):
            applied = lifecycle.apply_queued_confirmation_decisions(app, _LOG)

        assert applied == 1
        assert app.events.injected == [
            {"type": "confirmation_response", "id": "r1", "approved": True}
        ]
        assert not _queue_file(data_dir).exists()
        assert any(
            "applied 1 queued confirmation decision(s) from offline review"
            in r.getMessage()
            for r in caplog.records
        )

        # The injected event is what the event loop hands the resume handler.
        asyncio.run(
            root_handlers.on_confirmation_response(app, _LOG, app.events.injected[0])
        )
        assert app.dispatch.tasks == [_task()]
        assert app.dispatch.session_id == "goal-gone"

    def test_queued_partial_approve_carries_indices(self, data_dir, monkeypatch):
        details = [_detail("sys.execute_command", "pacman"), _detail("fs.delete", "rm")]
        _seed_store(data_dir, "batch", details=details)
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "batch", "0"])
        app = _restarted_app(data_dir)
        _stub_root_llm(monkeypatch)

        lifecycle.apply_queued_confirmation_decisions(app, _LOG)

        assert app.events.injected == [
            {"type": "confirmation_response", "id": "batch", "approved_indices": [0]}
        ]
        asyncio.run(
            root_handlers.on_confirmation_response(app, _LOG, app.events.injected[0])
        )
        assert app.dispatch.tasks == [_task("pacman")]

    def test_queued_approve_all_expands_over_the_restored_store(
        self, data_dir, monkeypatch
    ):
        _seed_store(data_dir, "one")
        _seed_store(data_dir, "two")
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve-all"])
        app = _restarted_app(data_dir)

        lifecycle.apply_queued_confirmation_decisions(app, _LOG)

        assert {m["id"] for m in app.events.injected} == {"one", "two"}
        assert all(m["approved"] is True for m in app.events.injected)

    def test_missing_id_is_skipped_and_the_queue_still_clears(
        self, data_dir, monkeypatch, caplog
    ):
        _seed_store(data_dir)
        _run_confirm(monkeypatch, ["jarvis", "confirm", "approve", "abc123"])
        # The daemon resolved abc123 through another channel before restarting.
        (data_dir / "confirmations.json").write_text("[]", encoding="utf-8")
        app = _restarted_app(data_dir)
        _stub_root_llm(monkeypatch)

        with caplog.at_level(logging.WARNING):
            lifecycle.apply_queued_confirmation_decisions(app, _LOG)

        assert not _queue_file(data_dir).exists()
        asyncio.run(
            root_handlers.on_confirmation_response(app, _LOG, app.events.injected[0])
        )
        assert app.dispatch.tasks is None

    def test_absent_queue_is_a_silent_no_op(self, data_dir, caplog):
        app = _restarted_app(data_dir)

        with caplog.at_level(logging.INFO):
            applied = lifecycle.apply_queued_confirmation_decisions(app, _LOG)

        assert applied == 0
        assert app.events.injected == []
        assert not any(
            "queued confirmation decision" in r.getMessage() for r in caplog.records
        )

    @pytest.mark.parametrize("body", ["{not json", '{"type": "approve_confirmation"}'])
    def test_corrupt_queue_is_preserved_as_bad_and_startup_survives(
        self, data_dir, caplog, body
    ):
        _queue_file(data_dir).write_text(body, encoding="utf-8")
        app = _restarted_app(data_dir)

        with caplog.at_level(logging.WARNING):
            applied = lifecycle.apply_queued_confirmation_decisions(app, _LOG)

        assert applied == 0
        assert not _queue_file(data_dir).exists()
        bad = data_dir / "confirmation_decisions.json.bad"
        assert bad.read_text(encoding="utf-8") == body
        assert any(
            "confirmation decision queue" in r.getMessage().lower()
            for r in caplog.records
        )

    def test_startup_wiring_applies_the_queue(self, data_dir, monkeypatch):
        """The apply must be wired into daemon startup, not merely callable —
        and only once the injector responses have somewhere to go."""
        app = MagicMock()
        app.voice_manager = None
        calls = []
        app.confirmation.set_event_injector.side_effect = lambda cb: calls.append(
            "wired"
        )
        monkeypatch.setattr(lifecycle.Config, "JARVIS_INPUT_SOCKET", "")
        monkeypatch.setattr(lifecycle.Config, "JARVIS_OUTPUT_SOCKET", "")
        monkeypatch.setattr(lifecycle.Config, "JARVIS_GUI_SOCKET", "")
        monkeypatch.setattr(lifecycle.Config, "UPDATE_CHECK_INTERVAL_MIN", 0)
        monkeypatch.setattr(lifecycle.Config, "OPENAI_SERVER_ENABLED", False)
        monkeypatch.setattr(
            lifecycle,
            "apply_queued_confirmation_decisions",
            lambda a, log: calls.append("applied") or 0,
        )

        asyncio.run(lifecycle.start_runtime_services(app, _LOG))

        assert calls == ["wired", "applied"]
