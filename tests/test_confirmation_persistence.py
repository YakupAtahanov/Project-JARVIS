"""#224 — pending confirmations must survive a daemon restart.

The pending list used to live only in ``ConfirmationManager._pending``, so a
restart dropped every outstanding request while its goal was archived (#146).
With a store path the list is mirrored to JSON on every mutation and restored
at construction — silently, as a review queue for ``jarvis confirm``.
"""

import asyncio
import json
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from jarvis.core.confirmation_manager import ConfirmationManager
from jarvis.dispatch.goal_manager import GoalManager
from jarvis.runtime import root_handlers

_LOG = logging.getLogger("test")


def _task(command="pacman"):
    return {
        "server": "sys",
        "tool": "execute_command",
        "params": {"command": command, "args": ["-Syu", "--noconfirm"]},
    }


def _detail(tool_name="sys.execute_command", command="pacman"):
    task = _task(command)
    return {"tool_name": tool_name, "task": task, "params": task["params"]}


def _silent_channels():
    """No desktop toast, no TTY prompt — the store is what's under test."""
    return (
        patch.object(ConfirmationManager, "_has_tty", return_value=False),
        patch.object(
            ConfirmationManager, "_has_desktop_notifications", return_value=False
        ),
    )


async def _request(mgr, request_id="r1", details=None, session_id=None):
    tty, desktop = _silent_channels()
    with tty, desktop:
        await mgr.request_confirmation(
            request_id=request_id,
            tasks=[d["task"] for d in (details or [_detail()])],
            tools_needing_confirmation=details or [_detail()],
            approved_tasks=[],
            denied_tools=[],
            timeout=0,
            session_id=session_id,
        )


def _read(store):
    return json.loads(store.read_text(encoding="utf-8"))


@pytest.mark.unit
class TestWriteOnMutation:
    def test_request_writes_and_resolve_removes(self, tmp_path):
        store = tmp_path / "confirmations.json"
        mgr = ConfirmationManager(store_path=str(store))
        mgr.set_event_injector(Mock())

        asyncio.run(_request(mgr, "abc123", session_id="goal-1"))

        records = _read(store)
        assert [r["request_id"] for r in records] == ["abc123"]
        assert records[0]["session_id"] == "goal-1"
        assert records[0]["tool_names"] == ["sys.execute_command"]
        assert records[0]["tasks"] == [_task()]
        # The file mirrors _pending exactly, not just approximately.
        assert {r["request_id"] for r in records} == set(mgr._pending)

        mgr.resolve({"id": "abc123", "approved": True})

        assert _read(store) == []
        assert mgr._pending == {}

    def test_second_request_keeps_the_first(self, tmp_path):
        store = tmp_path / "confirmations.json"
        mgr = ConfirmationManager(store_path=str(store))
        mgr.set_event_injector(Mock())

        asyncio.run(_request(mgr, "one"))
        asyncio.run(_request(mgr, "two"))

        assert {r["request_id"] for r in _read(store)} == {"one", "two"}

        mgr.resolve({"id": "one", "approved": False})
        assert {r["request_id"] for r in _read(store)} == {"two"}


@pytest.mark.unit
class TestRestore:
    def test_fresh_manager_restores_silently(self, tmp_path):
        store = tmp_path / "confirmations.json"
        first = ConfirmationManager(store_path=str(store))
        first.set_event_injector(Mock())
        asyncio.run(_request(first, "abc123", session_id="goal-1"))
        created_at = first._pending["abc123"].created_at

        injector = Mock()
        with patch.object(
            ConfirmationManager, "_send_notification", new=AsyncMock()
        ) as notify:
            second = ConfirmationManager(store_path=str(store))
        second.set_event_injector(injector)

        notify.assert_not_awaited()
        injector.assert_not_called()
        # A restored entry is a review-queue item: no timeout task is armed.
        assert second._timeout_tasks == {}

        listed = second.list_pending()
        assert len(listed) == 1
        assert listed[0]["id"] == "abc123"
        assert listed[0]["session_id"] == "goal-1"
        assert listed[0]["created_at"] == created_at
        assert listed[0]["tool_lines"] == first.list_pending()[0]["tool_lines"]

    def test_restored_entry_resolves(self, tmp_path):
        store = tmp_path / "confirmations.json"
        first = ConfirmationManager(store_path=str(store))
        first.set_event_injector(Mock())
        asyncio.run(_request(first, "abc123"))

        second = ConfirmationManager(store_path=str(store))
        pending = second.resolve({"id": "abc123", "approved": True})

        assert pending is not None
        assert pending.approved_tasks == [_task()]
        assert _read(store) == []

    def test_restored_entry_honours_approved_indices(self, tmp_path):
        """#187's per-task path must still work on a restored batch."""
        store = tmp_path / "confirmations.json"
        first = ConfirmationManager(store_path=str(store))
        first.set_event_injector(Mock())
        details = [
            _detail("sys.execute_command", "pacman"),
            _detail("fs.delete", "rm"),
        ]
        asyncio.run(_request(first, "batch", details=details))

        second = ConfirmationManager(store_path=str(store))
        pending = second.resolve({"id": "batch", "approved_indices": [0]})

        assert pending is not None
        assert pending.approved_tasks == [_task("pacman")]
        assert pending.denied_tools == ["fs.delete"]

    def test_absent_store_starts_empty(self, tmp_path):
        mgr = ConfirmationManager(store_path=str(tmp_path / "confirmations.json"))
        assert mgr.list_pending() == []
        assert not (tmp_path / "confirmations.json").exists()

    @pytest.mark.parametrize("body", ["{not json", '{"request_id": "x"}', "[1, 2, 3]"])
    def test_corrupt_store_warns_and_starts_empty(self, tmp_path, caplog, body):
        store = tmp_path / "confirmations.json"
        store.write_text(body, encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            mgr = ConfirmationManager(store_path=str(store))

        assert mgr.list_pending() == []
        if body == "[1, 2, 3]":
            # A list of non-records is readable — the junk entries are skipped.
            return
        assert any(
            "Could not read pending confirmations" in r.getMessage()
            for r in caplog.records
        )


@pytest.mark.unit
class TestMemoryOnlyDefault:
    def test_bare_manager_touches_no_files(self, tmp_path, monkeypatch):
        """Every existing bare ConfirmationManager() must stay filesystem-free."""
        from jarvis.config import Config

        monkeypatch.setattr(Config, "JARVIS_DATA_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        mgr = ConfirmationManager()
        mgr.set_event_injector(Mock())
        asyncio.run(_request(mgr, "abc123"))
        assert mgr.has_pending("abc123")
        mgr.resolve({"id": "abc123", "approved": True})

        assert list(tmp_path.iterdir()) == []

    def test_daemon_factory_wires_the_store(self, tmp_path, monkeypatch):
        """The daemon's manager is the one that gets a store path.

        Patches ``component_factory``'s own bound ``Config`` name: another test
        reloads ``jarvis.config`` and mints a second Config class, so a fresh
        import here can patch the wrong one depending on run order.
        """
        from pathlib import Path

        from jarvis.core import component_factory as cf

        monkeypatch.setattr(cf.Config, "JARVIS_DATA_DIR", str(tmp_path))
        mgr = cf.ComponentFactory.create_confirmation_manager()

        assert mgr._store_path == Path(tmp_path) / "confirmations.json"
        # Construction only reads; an empty daemon writes nothing yet.
        assert list(tmp_path.iterdir()) == []


class _FakeDispatch:
    def __init__(self):
        self.session_id = "UNSET"
        self.tasks = None

    async def send_tasks(self, tasks, session_id=None):
        self.session_id = session_id
        self.tasks = tasks
        return {
            "output": (
                "Signal window (last 1):\n"
                '[10:00:00] PID 7 INIT sys/execute_command {"command":"pacman"}\n'
            )
        }


class _FakeApp:
    def __init__(self, goals, confirmation):
        self.goals = goals
        self.confirmation = confirmation
        self.dispatch = _FakeDispatch()
        self.llm = object()
        self._gui_clients = None
        self.acted = None

    async def _act_on_root_response(self, response):
        self.acted = response


@pytest.mark.unit
class TestResumeAfterRestart:
    def test_restored_approval_dispatches_without_its_goal(
        self, tmp_path, monkeypatch, caplog
    ):
        """The owning goal is archived at shutdown (#146), so a confirmation
        restored after a restart resumes with no goal to link to."""
        store = tmp_path / "confirmations.json"
        first = ConfirmationManager(store_path=str(store))
        first.set_event_injector(Mock())
        asyncio.run(_request(first, "r1", session_id="goal-gone"))

        # Fresh daemon: new manager loaded from disk, empty goal tree.
        restarted = ConfirmationManager(store_path=str(store))
        app = _FakeApp(GoalManager(archive_dir=str(tmp_path)), restarted)

        monkeypatch.setattr(root_handlers, "build_root_context", lambda a, l, **k: "")
        monkeypatch.setattr(root_handlers, "emit_activity", lambda *a, **k: None)

        async def _fake_ask(a, l, c, **k):
            return {"action": "respond", "output": "ok"}

        monkeypatch.setattr(root_handlers, "ask_llm", _fake_ask)

        with caplog.at_level(logging.INFO):
            asyncio.run(
                root_handlers.on_confirmation_response(
                    app, _LOG, {"id": "r1", "approved": True}
                )
            )

        assert app.dispatch.tasks == [_task()]
        assert app.dispatch.session_id == "goal-gone"
        assert app.goals.get_goal("goal-gone") is None
        assert any(
            "resumed without goal goal-gone" in r.getMessage() for r in caplog.records
        )
        assert _read(store) == []
