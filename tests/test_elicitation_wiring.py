"""Runtime wiring for a server's mid-task question (#210).

The pure policy (who answers) is pinned by test_elicitation_gate.py. These tests
pin the *wiring*: a NEEDS_ACTION signal reaching the daemon is routed on its
disposition, the model answers only ROOT-disposition benign prompts, a human
answers HUMAN-disposition ones (including every credential prompt), and every
failure resolves to a decline rather than stranding the parked task.

The adapter/confirmation surfaces are faked — no live dispatch binary is needed.
"""

import asyncio
import logging

import pytest

from jarvis.core import elicitation
from jarvis.core.command_parser import TaskParser
from jarvis.runtime import elicitation_flow, root_actions, root_handlers

_LOG = logging.getLogger("test")


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeDispatch:
    def __init__(self, respond_raises=False):
        self.responded = []  # (pid, action, content)
        self.sent = None
        self._respond_raises = respond_raises

    async def respond(self, pid, action, content=None):
        if self._respond_raises:
            raise RuntimeError("dispatch went away")
        self.responded.append((pid, action, content))
        return {"ok": True}

    async def send_tasks(self, tasks, session_id=None):
        self.sent = list(tasks)
        return {"output": ""}


class _FakeConfirmation:
    """A confirmation surface that records the prompt and can auto-answer.

    ``answer`` None means "no one answers" (drives the timeout/decline path);
    True/False simulate a human approving/denying by feeding the answer back
    through the real intercept, exactly as a real channel would.
    """

    def __init__(self, has_channel=True, answer=None, request_raises=False):
        self.app = None
        self.has_channel = has_channel
        self.answer = answer
        self.request_raises = request_raises
        self.presented = []  # (request_id, prompt_text, server)

    def has_live_channel(self, notification_silent=False):
        return self.has_channel

    async def request_prompt_decision(
        self, request_id, prompt_text, server=None, notification_silent=False, timeout=0.0
    ):
        if self.request_raises:
            raise RuntimeError("no channel actually reachable")
        self.presented.append((request_id, prompt_text, server))
        if self.answer is not None:
            elicitation_flow.handle_elicitation_confirmation(
                self.app, _LOG, {"id": request_id, "approved": self.answer}
            )


class _Recorder:
    def emit_activity(self, text="", kind="activity"):
        pass

    def handle_response(self, response):
        pass


class _FakeApp:
    def __init__(self, dispatch=None, confirmation=None, llm=object()):
        self.dispatch = dispatch if dispatch is not None else _FakeDispatch()
        self.confirmation = confirmation
        self.llm = llm
        self.output_manager = _Recorder()
        self.task_parser = TaskParser()
        self._needs_action_prompts = {}
        self._elicitation_futures = {}
        self.acted = None
        if confirmation is not None:
            confirmation.app = self

    async def _act_on_root_response(self, response, depth=0):
        self.acted = response


def _needs_action(pid=5, server="com.acme.tool", message="Continue? [Y/n]", schema=None, url=None):
    sig = {"type": "NEEDS_ACTION", "pid": pid, "server": server, "message": message, "untrusted": True}
    if schema is not None:
        sig["schema"] = schema
    if url is not None:
        sig["url"] = url
    return sig


@pytest.fixture
def surfaced(monkeypatch):
    """Capture the context handed to the model on the ROOT path."""
    seen = {}

    async def _fake_ask(app, logger, context, **kwargs):
        seen["context"] = context
        return {"action": "respond", "output": "ok"}

    # _surface_to_root imports these lazily from their home modules.
    import jarvis.runtime.llm_bridge as llm_bridge
    import jarvis.runtime.root_context as root_context

    monkeypatch.setattr(root_context, "build_root_context", lambda a, l, **k: "")
    monkeypatch.setattr(llm_bridge, "ask_llm", _fake_ask)
    return seen


# ---------------------------------------------------------------------------
# ROOT path: the model is offered the attributed prompt
# ---------------------------------------------------------------------------


class TestRootDisposition:
    def test_benign_prompt_is_offered_to_the_model_attributed(self, surfaced, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "smart", raising=False)
        app = _FakeApp()

        asyncio.run(
            elicitation_flow.route_needs_action(app, _LOG, _needs_action(pid=5))
        )

        ctx = surfaced["context"]
        # Attributed, not raw: it must read as the server asking.
        assert "The MCP server 'com.acme.tool' is asking:" in ctx
        assert "Continue? [Y/n]" in ctx  # the question, inside the attribution
        assert "NEEDS_ACTION" in ctx
        assert "answer_prompt" in ctx
        assert "pid: 5" in ctx
        # The model was asked; no human surface, no direct answer yet.
        assert app.dispatch.responded == []
        # The prompt is stashed for the answer_prompt handler.
        assert 5 in app._needs_action_prompts
        assert app._needs_action_prompts[5]["disposition"] == "root"

    def test_root_prompt_with_no_llm_declines_rather_than_hangs(self, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "allow_all", raising=False)
        app = _FakeApp(llm=None)

        asyncio.run(
            elicitation_flow.route_needs_action(app, _LOG, _needs_action(pid=9))
        )

        assert app.dispatch.responded == [(9, "decline", None)]


# ---------------------------------------------------------------------------
# HUMAN path: the model does not answer; a human does
# ---------------------------------------------------------------------------


class TestHumanDisposition:
    def test_ask_all_routes_to_the_human_surface_not_the_model(self, surfaced, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "ask_all", raising=False)
        conf = _FakeConfirmation(has_channel=True, answer=True)
        app = _FakeApp(confirmation=conf)

        asyncio.run(
            elicitation_flow.route_needs_action(app, _LOG, _needs_action(pid=3))
        )

        # Human approved → the task is answered accept, by the human, not the model.
        assert app.dispatch.responded == [(3, "accept", None)]
        # The model was never consulted.
        assert "context" not in surfaced
        assert app._needs_action_prompts == {}
        # The human saw the attributed prompt, never the raw message alone.
        assert len(conf.presented) == 1
        _rid, prompt_text, server = conf.presented[0]
        assert prompt_text == elicitation.attribute("com.acme.tool", "Continue? [Y/n]")
        assert server == "com.acme.tool"

    def test_human_decline_answers_decline(self, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "ask_all", raising=False)
        conf = _FakeConfirmation(has_channel=True, answer=False)
        app = _FakeApp(confirmation=conf)

        asyncio.run(
            elicitation_flow.route_needs_action(app, _LOG, _needs_action(pid=4))
        )

        assert app.dispatch.responded == [(4, "decline", None)]


# ---------------------------------------------------------------------------
# Credential boundary: HUMAN in every mode; no human → DECLINE, never accept
# ---------------------------------------------------------------------------


class TestCredentialBoundary:
    @pytest.mark.parametrize("mode", ["allow_all", "smart", "ask_all"])
    def test_credential_prompt_never_reaches_the_model(self, surfaced, monkeypatch, mode):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", mode, raising=False)
        # A live human channel that would approve — proving that even so, the
        # decision goes to the human, never to the model.
        conf = _FakeConfirmation(has_channel=True, answer=True)
        app = _FakeApp(confirmation=conf)

        asyncio.run(
            elicitation_flow.route_needs_action(
                app, _LOG, _needs_action(pid=7, message="[sudo] password for user:")
            )
        )

        assert "context" not in surfaced  # model never asked
        assert app._needs_action_prompts == {}  # nothing stashed for the model
        assert len(conf.presented) == 1  # the human was asked
        assert app.dispatch.responded == [(7, "accept", None)]  # by the human

    @pytest.mark.parametrize("mode", ["allow_all", "smart", "ask_all"])
    def test_credential_with_no_human_is_declined_not_accepted(self, monkeypatch, mode):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", mode, raising=False)
        conf = _FakeConfirmation(has_channel=False)  # nobody to answer
        app = _FakeApp(confirmation=conf)

        asyncio.run(
            elicitation_flow.route_needs_action(
                app, _LOG, _needs_action(pid=8, message="Please enter your API key")
            )
        )

        # The inviolable rule: no human, a credential is DECLINED — never a guess.
        assert app.dispatch.responded == [(8, "decline", None)]
        assert conf.presented == []  # not even presented — declined immediately

    def test_password_field_in_schema_is_a_credential(self, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "allow_all", raising=False)
        conf = _FakeConfirmation(has_channel=False)
        app = _FakeApp(confirmation=conf)
        schema = {"properties": {"password": {"type": "string"}}}

        asyncio.run(
            elicitation_flow.route_needs_action(
                app, _LOG, _needs_action(pid=2, message="Enter value:", schema=schema)
            )
        )

        assert app.dispatch.responded == [(2, "decline", None)]


# ---------------------------------------------------------------------------
# Never hang: a dropped/failed/absent answer becomes a decline
# ---------------------------------------------------------------------------


class TestNeverHang:
    def test_human_timeout_becomes_a_decline(self, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "ask_all", raising=False)
        monkeypatch.setattr(elicitation_flow, "_HUMAN_TIMEOUT", 0.05)
        conf = _FakeConfirmation(has_channel=True, answer=None)  # never answers
        app = _FakeApp(confirmation=conf)

        asyncio.run(
            elicitation_flow.route_needs_action(app, _LOG, _needs_action(pid=6))
        )

        assert app.dispatch.responded == [(6, "decline", None)]
        assert app._elicitation_futures == {}  # future cleaned up

    def test_presenting_the_prompt_failing_becomes_a_decline(self, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "ask_all", raising=False)
        conf = _FakeConfirmation(has_channel=True, request_raises=True)
        app = _FakeApp(confirmation=conf)

        asyncio.run(
            elicitation_flow.route_needs_action(app, _LOG, _needs_action(pid=1))
        )

        assert app.dispatch.responded == [(1, "decline", None)]
        assert app._elicitation_futures == {}

    def test_dispatch_respond_raising_does_not_propagate(self):
        app = _FakeApp(dispatch=_FakeDispatch(respond_raises=True))

        # respond_to_prompt must swallow the failure and report it, not raise.
        result = asyncio.run(
            elicitation_flow.respond_to_prompt(app, _LOG, 5, "decline")
        )
        assert "error" in result

    def test_no_dispatch_adapter_reports_error_without_raising(self):
        app = _FakeApp()
        app.dispatch = object()  # no respond attribute

        result = asyncio.run(
            elicitation_flow.respond_to_prompt(app, _LOG, 5, "decline")
        )
        assert "error" in result


# ---------------------------------------------------------------------------
# answer_prompt handler: the model's answer to a ROOT prompt
# ---------------------------------------------------------------------------


def _run_answer(app, parsed):
    asyncio.run(
        root_actions.act_on_root_response(
            app, _LOG, parsed, depth=0, max_chain_depth=15
        )
    )


class TestAnswerPromptHandler:
    def _stash_benign(self, app, pid=5):
        app._needs_action_prompts[pid] = elicitation.describe(
            {"pid": pid, "server": "com.acme.tool", "message": "Which disk? [a/b]"},
            "smart",
        )

    def test_accept_delivers_content_to_the_task(self):
        app = _FakeApp()
        self._stash_benign(app, pid=5)
        _run_answer(
            app,
            {"action": "answer_prompt", "pid": 5, "decision": "accept", "content": {"disk": "a"}},
        )
        assert app.dispatch.responded == [(5, "accept", {"disk": "a"})]
        assert 5 not in app._needs_action_prompts  # un-stashed

    def test_decline_drops_content(self):
        app = _FakeApp()
        self._stash_benign(app, pid=5)
        _run_answer(
            app,
            {"action": "answer_prompt", "pid": 5, "decision": "decline", "content": {"x": 1}},
        )
        assert app.dispatch.responded == [(5, "decline", None)]

    def test_unknown_decision_becomes_decline(self):
        app = _FakeApp()
        self._stash_benign(app, pid=5)
        _run_answer(app, {"action": "answer_prompt", "pid": 5, "decision": "maybe"})
        assert app.dispatch.responded == [(5, "decline", None)]

    def test_model_escalation_routes_to_a_human(self):
        conf = _FakeConfirmation(has_channel=True, answer=False)
        app = _FakeApp(confirmation=conf)
        self._stash_benign(app, pid=5)
        _run_answer(
            app,
            {"action": "answer_prompt", "pid": 5, "decision": "accept", "escalate": True},
        )
        # Escalated → the human decided (declined here), the model did not.
        assert len(conf.presented) == 1
        assert app.dispatch.responded == [(5, "decline", None)]

    def test_model_cannot_accept_a_credential_even_if_stashed(self):
        # Defense in depth: if a credential ever reaches the model's answer path,
        # the handler re-checks and refuses to let the model accept it.
        conf = _FakeConfirmation(has_channel=False)  # no human → decline
        app = _FakeApp(confirmation=conf)
        app._needs_action_prompts[5] = {
            "pid": 5,
            "server": "com.acme.tool",
            "message": "Enter your password",
            "schema": None,
            "credential": True,
            "prompt_text": elicitation.attribute("com.acme.tool", "Enter your password"),
        }
        _run_answer(
            app,
            {"action": "answer_prompt", "pid": 5, "decision": "accept", "content": {"password": "hunter2"}},
        )
        # Never accepted with the model's guessed secret.
        assert app.dispatch.responded == [(5, "decline", None)]


# ---------------------------------------------------------------------------
# Integration: on_dispatch_signal / on_confirmation_response
# ---------------------------------------------------------------------------


class TestSignalHandlerIntegration:
    def test_on_dispatch_signal_routes_needs_action(self, surfaced, monkeypatch):
        monkeypatch.setattr(elicitation_flow.Config, "CONFIRMATION_MODE", "smart", raising=False)
        app = _FakeApp()

        asyncio.run(
            root_handlers.on_dispatch_signal(app, _LOG, _needs_action(pid=11))
        )

        # It went through the elicitation path (model surfaced), not the generic
        # EXIT path (which would have called app._act_on_root_response via ask_llm
        # with a SIGNAL context, and would not stash a prompt).
        assert 11 in app._needs_action_prompts
        assert "NEEDS_ACTION" in surfaced["context"]

    def test_on_confirmation_response_intercepts_elicitation_answers(self):
        app = _FakeApp(confirmation=_FakeConfirmation())
        loop = asyncio.new_event_loop()
        try:
            fut = loop.create_future()
            app._elicitation_futures["abc"] = fut
            # An elicitation answer is consumed by the intercept and sets the future.
            handled = elicitation_flow.handle_elicitation_confirmation(
                app, _LOG, {"id": "abc", "approved": True}
            )
            assert handled is True
            assert fut.result() is True
        finally:
            loop.close()

    def test_on_confirmation_response_passes_through_normal_confirmations(self):
        # A confirmation id that is NOT an elicitation must not be intercepted.
        app = _FakeApp()
        handled = elicitation_flow.handle_elicitation_confirmation(
            app, _LOG, {"id": "not-an-elicitation", "approved": True}
        )
        assert handled is False


# ---------------------------------------------------------------------------
# Field extraction: attribution survives the shapes a signal can arrive in
# ---------------------------------------------------------------------------


class TestFieldExtraction:
    def test_top_level_fields(self):
        f = elicitation_flow._extract_fields(_needs_action(pid=5, url="https://x"))
        assert f["pid"] == 5
        assert f["server"] == "com.acme.tool"
        assert f["message"] == "Continue? [Y/n]"
        assert f["url"] == "https://x"

    def test_payload_nested_fields_fall_back(self):
        # A pushed signal that nests the elicitation fields under payload, with
        # the message normalized into data, still attributes correctly.
        sig = {
            "type": "NEEDS_ACTION",
            "pid": 5,
            "data": "Which region?",
            "payload": {"server": "com.acme.tool", "schema": {"x": 1}},
        }
        f = elicitation_flow._extract_fields(sig)
        assert f["server"] == "com.acme.tool"
        assert f["message"] == "Which region?"
        assert f["schema"] == {"x": 1}
