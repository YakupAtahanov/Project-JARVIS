"""CONFIG_HINT must reach the LLM from the EXIT-signal path.

#195 made the dispatch path go silent (EXIT signals drive the next ROOT turn),
which silently took the old dispatch_flow CONFIG_HINT builder out of the loop.
Re-homed into root_handlers' two signal handlers: when an EXIT carries an
auth/token error, the context must name the failing server's exact config keys
so the LLM can call configure_server instead of re-running the same bad call
until the #205 repeat guard kills the goal.
"""

import asyncio
import logging

from jarvis.dispatch.goal_manager import GoalManager
from jarvis.runtime import root_handlers

_LOG = logging.getLogger("test")

_MANIFEST = {
    "configurableProperties": [
        {"key": "BRAVE_API_KEY", "label": "Brave API key"},
        {"key": "BRAVE_ENDPOINT", "label": "Endpoint"},
    ]
}


class _FakeDispatch:
    def __init__(self, manifest=None):
        self.manifest = _MANIFEST if manifest is None else manifest
        self.asked_for = []

    async def get_server_manifest(self, server_id):
        self.asked_for.append(server_id)
        return self.manifest


class _FakeSessions:
    current_id = "s1"

    def load_summary(self):
        return ""


class _FakeApp:
    def __init__(self, goals, manifest=None):
        self.goals = goals
        self.dispatch = _FakeDispatch(manifest)
        self.sessions = _FakeSessions()
        self.llm = object()  # not None
        self.acted = None

    async def _act_on_root_response(self, response, depth=0):
        self.acted = response


def _exit_signal(pid, output):
    return {"type": "EXIT", "pid": pid, "data": {"output": output}}


def _wire(monkeypatch):
    """Stub context building + the LLM call; capture the context handed to it."""
    seen = {}

    monkeypatch.setattr(root_handlers, "build_root_context", lambda a, l, **k: "")
    monkeypatch.setattr(root_handlers, "emit_activity", lambda *a, **k: None)

    async def _fake_ask(a, l, context, **k):
        seen["context"] = context
        return {"action": "respond", "output": "ok"}

    monkeypatch.setattr(root_handlers, "ask_llm", _fake_ask)
    return seen


def _goal_with_dispatch(tmp_path, server="com.brave.search", pid=7):
    goals = GoalManager(archive_dir=str(tmp_path))
    goal = goals.add_goal("search the web")
    goals.link_tasks(goal.id, [pid])
    # Fingerprint format is server<US>tool<US>params, batches joined by <RS>.
    fingerprint = f"{server}\x1fbrave_search\x1f{{}}"
    goals.link_dispatch_fingerprint(goal.id, fingerprint, [pid])
    return goals, goal


class TestSingleSignal:
    def test_auth_error_exit_adds_config_hint_with_manifest_keys(
        self, tmp_path, monkeypatch
    ):
        goals, _goal = _goal_with_dispatch(tmp_path)
        app = _FakeApp(goals)
        seen = _wire(monkeypatch)

        asyncio.run(
            root_handlers.on_dispatch_signal(
                app,
                _LOG,
                _exit_signal(7, "error: SUBSCRIPTION_TOKEN_INVALID (422)"),
            )
        )

        ctx = seen["context"]
        assert "CONFIG_HINT" in ctx
        assert "com.brave.search" in ctx
        # The exact key names from the manifest, not guessed from error wording.
        assert "BRAVE_API_KEY" in ctx
        assert "BRAVE_ENDPOINT" in ctx
        assert '"action": "configure_server"' in ctx
        assert app.dispatch.asked_for == ["com.brave.search"]

    def test_non_auth_error_exit_adds_no_hint(self, tmp_path, monkeypatch):
        goals, _goal = _goal_with_dispatch(tmp_path)
        app = _FakeApp(goals)
        seen = _wire(monkeypatch)

        asyncio.run(
            root_handlers.on_dispatch_signal(
                app, _LOG, _exit_signal(7, "error: connection timed out")
            )
        )

        assert "CONFIG_HINT" not in seen["context"]
        # No manifest lookup at all when nothing looks like an auth failure.
        assert app.dispatch.asked_for == []

    def test_server_with_no_configurable_properties_adds_no_hint(
        self, tmp_path, monkeypatch
    ):
        goals, _goal = _goal_with_dispatch(tmp_path)
        app = _FakeApp(goals, manifest={"configurableProperties": []})
        seen = _wire(monkeypatch)

        asyncio.run(
            root_handlers.on_dispatch_signal(app, _LOG, _exit_signal(7, "unauthorized"))
        )

        assert "CONFIG_HINT" not in seen["context"]

    def test_manifest_lookup_failure_does_not_break_the_turn(
        self, tmp_path, monkeypatch
    ):
        goals, _goal = _goal_with_dispatch(tmp_path)
        app = _FakeApp(goals)

        async def _boom(server_id):
            raise RuntimeError("registry unreachable")

        app.dispatch.get_server_manifest = _boom
        seen = _wire(monkeypatch)

        asyncio.run(
            root_handlers.on_dispatch_signal(
                app, _LOG, _exit_signal(7, "invalid_api_key")
            )
        )

        assert "CONFIG_HINT" not in seen["context"]
        assert app.acted == {"action": "respond", "output": "ok"}


class TestBatchedSignals:
    def test_auth_error_in_batch_adds_config_hint(self, tmp_path, monkeypatch):
        goals, _goal = _goal_with_dispatch(tmp_path)
        app = _FakeApp(goals)
        seen = _wire(monkeypatch)

        asyncio.run(
            root_handlers.on_dispatch_signals(
                app,
                _LOG,
                [_exit_signal(7, "error: Unauthorized — token_invalid")],
            )
        )

        ctx = seen["context"]
        assert "CONFIG_HINT" in ctx
        assert "BRAVE_API_KEY" in ctx

    def test_clean_batch_adds_no_hint(self, tmp_path, monkeypatch):
        goals, _goal = _goal_with_dispatch(tmp_path)
        app = _FakeApp(goals)
        seen = _wire(monkeypatch)

        asyncio.run(
            root_handlers.on_dispatch_signals(
                app, _LOG, [_exit_signal(7, "Python 3.11.15")]
            )
        )

        assert "CONFIG_HINT" not in seen["context"]

    def test_server_id_falls_back_to_signal_payload(self, tmp_path, monkeypatch):
        """No fingerprint mapping (e.g. a goal-less task) — use the signal field."""
        goals = GoalManager(archive_dir=str(tmp_path))
        app = _FakeApp(goals)
        seen = _wire(monkeypatch)

        sig = _exit_signal(99, "invalid_token")
        sig["server"] = "com.example.thing"

        asyncio.run(root_handlers.on_dispatch_signals(app, _LOG, [sig]))

        assert "CONFIG_HINT" in seen["context"]
        assert "com.example.thing" in seen["context"]
