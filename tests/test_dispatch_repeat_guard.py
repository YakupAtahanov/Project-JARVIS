"""#205 — per-goal dispatch repeat/progress guard.

EXIT-driven ROOT turns re-enter _act_on_root_response at depth 0, so the
synchronous MAX_CHAIN_DEPTH cap never bounds a tool that keeps returning no
usable content across dispatch cycles (observed: navigate -> about:blank looped
~8x until a provider read-timeout). This guard counts identical
(server, tool, params) dispatches within one goal and short-circuits to an
informative respond before re-sending a no-progress tool.

Also covers the secondary task_pids dedup fix (loop_body.md bottom section).
"""

import asyncio
import logging

import pytest

from jarvis.config import Config
from jarvis.dispatch.goal_manager import GoalManager
from jarvis.runtime import dispatch_flow

_LOG = logging.getLogger("test")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _FakeDispatch:
    is_connected = True


class _OutputManager:
    def __init__(self):
        self.responses = []

    def handle_response(self, payload):
        self.responses.append(payload)

    def emit_activity(self, *a, **k):
        pass


class _App:
    def __init__(self, goals):
        self.goals = goals
        self.dispatch = _FakeDispatch()
        self.contextor = None  # persist_assistant_turn no-ops
        self.mcp_dispatch_docs = {}
        self.output_manager = _OutputManager()
        self.acted = []

    async def _act_on_root_response(self, response, depth=0):
        self.acted.append((response, depth))


def _sender(state):
    """A fake dispatch_send that hands back an incrementing INIT PID."""

    async def _fake_send(app, logger, tasks, session_id=None):
        state["pid"] += 1
        pid = state["pid"]
        state["sends"] += 1
        return {
            "output": (
                f"Signal window (last 1):\n" f"[10:00:00] PID {pid} INIT s/t {{}}\n"
            )
        }

    return _fake_send


def _patch(monkeypatch, state, limit=3):
    monkeypatch.setattr(Config, "DISPATCH_REPEAT_LIMIT", limit)
    monkeypatch.setattr(dispatch_flow, "dispatch_send", _sender(state))
    monkeypatch.setattr(dispatch_flow, "emit_activity", lambda *a, **k: None)


def _nav():
    return [
        {
            "server": "playwright",
            "tool": "browser_navigate",
            "params": {"url": "https://github.com/YakupAtahanov"},
        }
    ]


def _snap():
    return [{"server": "playwright", "tool": "browser_snapshot", "params": {}}]


def _exit(pid, output=""):
    return {"type": "EXIT", "pid": pid, "data": output}


# ---------------------------------------------------------------------------
# GoalManager.record_dispatch — the window-count primitive
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_record_dispatch_counts_within_window(tmp_path):
    gm = GoalManager(archive_dir=str(tmp_path))
    goal = gm.add_goal("x")
    assert gm.record_dispatch(goal.id, "A") == 1
    assert gm.record_dispatch(goal.id, "A") == 2
    assert gm.record_dispatch(goal.id, "B") == 1
    assert gm.record_dispatch(goal.id, "A") == 3  # not consecutive, still counts


@pytest.mark.unit
def test_record_dispatch_catches_interleaved_cycle(tmp_path):
    gm = GoalManager(archive_dir=str(tmp_path))
    goal = gm.add_goal("x")
    # A,B,A,B,A — A must reach 3 even though no two A's are adjacent.
    counts = [gm.record_dispatch(goal.id, fp) for fp in ("A", "B", "A", "B", "A")]
    assert counts[-1] == 3


@pytest.mark.unit
def test_record_dispatch_trims_to_window(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DISPATCH_REPEAT_WINDOW", 4)
    gm = GoalManager(archive_dir=str(tmp_path))
    goal = gm.add_goal("x")
    for fp in ("A", "B", "C", "D", "E"):  # A ages out of a 4-wide window
        gm.record_dispatch(goal.id, fp)
    assert goal.recent_dispatches == ["B", "C", "D", "E"]
    assert gm.record_dispatch(goal.id, "A") == 1


@pytest.mark.unit
def test_record_dispatch_unknown_goal_is_zero(tmp_path):
    gm = GoalManager(archive_dir=str(tmp_path))
    assert gm.record_dispatch("nope", "A") == 0


# ---------------------------------------------------------------------------
# Guard at the dispatch choke point
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pure_repeat_trips_and_stays_silent(tmp_path, monkeypatch):
    state = {"pid": 1, "sends": 0}
    _patch(monkeypatch, state, limit=3)
    monkeypatch.setattr(dispatch_flow, "ask_llm", _boom("guard must not call the LLM"))

    gm = GoalManager(archive_dir=str(tmp_path))
    gm.add_goal("fetch page")
    app = _App(gm)

    for _ in range(5):
        if app.output_manager.responses:
            break
        asyncio.run(dispatch_flow.dispatch_execute_tasks(app, _LOG, _nav(), depth=0))

    # Trips on the 3rd send attempt: 2 sends, 3rd short-circuited.
    assert state["sends"] == 2
    assert len(app.output_manager.responses) == 1
    assert "browser_navigate" in app.output_manager.responses[0]["output"]
    # No LLM turn was driven.
    assert app.acted == []
    # Goal is failed + dismissed so it stops re-driving.
    assert gm.get_all_goals() == []


@pytest.mark.unit
def test_interleaved_navigate_snapshot_loop_terminates(tmp_path, monkeypatch):
    """Regression: replay navigate -> about:blank -> snapshot('') -> ... and
    prove it terminates in <= limit x cycle-length dispatches with an
    informative respond, instead of looping until a provider timeout."""
    state = {"pid": 1, "sends": 0}
    _patch(monkeypatch, state, limit=3)
    monkeypatch.setattr(dispatch_flow, "ask_llm", _boom("guard must not call the LLM"))

    gm = GoalManager(archive_dir=str(tmp_path))
    gm.add_goal("fetch github page")
    app = _App(gm)

    cycle = [_nav, _snap]
    for i in range(20):
        if app.output_manager.responses:
            break
        asyncio.run(
            dispatch_flow.dispatch_execute_tasks(app, _LOG, cycle[i % 2](), depth=0)
        )
        # Every EXIT comes back empty — no progress.
        gm.update_from_signal(_exit(state["pid"], output=""))

    assert app.output_manager.responses, "loop never short-circuited"
    # limit(3) x cycle length(2) = 6 upper bound on real sends.
    assert state["sends"] <= 6
    assert "browser_navigate" in app.output_manager.responses[0]["output"]
    assert gm.get_all_goals() == []


@pytest.mark.unit
def test_new_params_each_time_does_not_trip(tmp_path, monkeypatch):
    state = {"pid": 1, "sends": 0}
    _patch(monkeypatch, state, limit=3)

    gm = GoalManager(archive_dir=str(tmp_path))
    gm.add_goal("browse several pages")
    app = _App(gm)

    for i in range(6):
        task = [
            {
                "server": "playwright",
                "tool": "browser_navigate",
                "params": {"url": f"https://example.com/{i}"},
            }
        ]
        asyncio.run(dispatch_flow.dispatch_execute_tasks(app, _LOG, task, depth=0))

    assert app.output_manager.responses == []
    assert state["sends"] == 6


@pytest.mark.unit
def test_poll_until_ready_with_changing_exits_does_not_trip(tmp_path, monkeypatch):
    """Same tool + same params each poll, but each EXIT returns new content —
    the progress reset must age the window out so it never trips."""
    state = {"pid": 1, "sends": 0}
    _patch(monkeypatch, state, limit=3)

    gm = GoalManager(archive_dir=str(tmp_path))
    gm.add_goal("wait for job")
    app = _App(gm)

    poll = [{"server": "ci", "tool": "check_status", "params": {"job": 7}}]
    progress = ["10%", "25%", "50%", "75%", "90%", "done"]
    for text in progress:
        asyncio.run(dispatch_flow.dispatch_execute_tasks(app, _LOG, poll, depth=0))
        gm.update_from_signal(_exit(state["pid"], output=text))

    assert app.output_manager.responses == []
    assert state["sends"] == len(progress)


# ---------------------------------------------------------------------------
# Progress detection is nonce-independent (boundary-wrapped output)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_identical_inner_content_under_different_nonces_is_not_progress(tmp_path):
    gm = GoalManager(archive_dir=str(tmp_path))
    goal = gm.add_goal("x")
    gm.record_dispatch(goal.id, "fp")
    gm.record_dispatch(goal.id, "fp")
    gm.link_tasks(goal.id, [1, 2])
    gm.link_dispatch_fingerprint(goal.id, "fp", [1, 2])

    # Same inner content "X", different per-task nonces — the wrapper bytes
    # differ but the tool made no progress, so the window must survive.
    gm.update_from_signal(
        {
            "type": "EXIT",
            "pid": 1,
            "data": "[hash=aaa] 200 <aaa>X</aaa>",
            "nonce": "aaa",
        }
    )
    gm.update_from_signal(
        {
            "type": "EXIT",
            "pid": 2,
            "data": "[hash=bbb] 200 <bbb>X</bbb>",
            "nonce": "bbb",
        }
    )
    assert goal.recent_dispatches == ["fp", "fp"]


@pytest.mark.unit
def test_changed_inner_content_resets_window(tmp_path):
    gm = GoalManager(archive_dir=str(tmp_path))
    goal = gm.add_goal("x")
    gm.record_dispatch(goal.id, "fp")
    gm.record_dispatch(goal.id, "fp")
    gm.link_tasks(goal.id, [1, 2])
    gm.link_dispatch_fingerprint(goal.id, "fp", [1, 2])

    gm.update_from_signal(
        {
            "type": "EXIT",
            "pid": 1,
            "data": "[hash=aaa] 200 <aaa>X</aaa>",
            "nonce": "aaa",
        }
    )
    gm.update_from_signal(
        {
            "type": "EXIT",
            "pid": 2,
            "data": "[hash=bbb] 200 <bbb>Y</bbb>",
            "nonce": "bbb",
        }
    )
    assert goal.recent_dispatches == []


# ---------------------------------------------------------------------------
# Secondary: task_pids dedup (loop_body.md bottom section)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_link_tasks_dedups_replayed_pids(tmp_path):
    """_extract_pids_from_result re-offers earlier INITs from the rolling
    signal window, so link_tasks must not grow [2] -> [2,2,3] -> [2,2,3,2,3,4]."""
    gm = GoalManager(archive_dir=str(tmp_path))
    goal = gm.add_goal("x")
    gm.link_tasks(goal.id, [2])
    gm.link_tasks(goal.id, [2, 3])  # window still holds PID 2's INIT
    gm.link_tasks(goal.id, [2, 3, 4])
    assert goal.task_pids == [2, 3, 4]


def _boom(msg):
    async def _fail(*a, **k):
        raise AssertionError(msg)

    return _fail
