"""Who answers a question a server asked mid-task.

A running MCP server can ask for input *during* a tool call (MCP's
``elicitation/create``); dispatch surfaces that as a ``NEEDS_ACTION`` signal on a
task that is alive and blocked. This module decides one thing: may ROOT answer
it, or must a human?

The dial already exists. ``CONFIRMATION_MODE`` governs every other "may the
model act unattended" question, and an elicited prompt is the same question in a
different costume, so it maps straight onto the three modes rather than growing a
fourth setting nobody would think to configure:

===============  ==========================================================
``allow_all``    ROOT answers.
``smart``        ``classify()`` decides — ELEVATED or above goes to a human.
``ask_all``      A human answers every one.
===============  ==========================================================

**In ``smart`` the escalation is deterministic, and that is the whole point.**
It is not "the model escalates when it feels unsure": a prompt-injected or
confidently-wrong model does not feel unsure, so a gate resting on the model's
self-report is no gate at all. The prompt text and the model's proposed answer go
through the same :func:`classify` that governs tool calls — host floor, declared
level, payload scan — and a hit escalates regardless of what the model thinks.

The asymmetry is raise-only, mirroring how a manifest may raise a tool's threat
level but never lower it below the host floor: the model may **always** ask for a
human (escalating is never unsafe), and may **never** suppress an escalation
``classify()`` decided.

Two boundaries hold in every mode, including ``allow_all``:

* **A credential prompt is never answered by the model.** This is correctness
  before it is policy — the model does not hold the user's password, so there is
  nothing for it to answer with and a confident guess is worse than silence. It
  goes to a human or the task is declined.
* **The prompt text is the server's, not ours.** It is authored by whoever wrote
  the server, which for a community server is neither the user nor us, so it is
  always attributed. A renderer must say *the server X is asking*, never present
  it as JARVIS asking — otherwise a community server phishing for a password
  borrows the assistant's credibility to do it.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Optional

from .threat_level import ThreatLevel, classify

__all__ = [
    "PromptDisposition",
    "is_credential_prompt",
    "decide",
    "attribute",
    "describe",
]


class PromptDisposition(str, Enum):
    """Who may answer a question a server asked."""

    #: ROOT may answer unattended.
    ROOT = "root"
    #: A human must answer; the model may not.
    HUMAN = "human"


# Shapes a request for a secret takes. Matched against the prompt text, which is
# the server's own wording — deliberately broad, because the cost of routing an
# ordinary question to a human is a moment of friction, while the cost of letting
# a model improvise a credential is a leaked or fabricated secret. When in doubt,
# a human decides.
_CREDENTIAL_PATTERNS = (
    re.compile(r"\bpass(?:word|phrase)\b", re.IGNORECASE),
    re.compile(r"\bpasswd\b", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
    re.compile(r"\bcredential", re.IGNORECASE),
    re.compile(r"\b(?:api[_\- ]?key|access[_\- ]?token|auth[_\- ]?token)\b", re.IGNORECASE),
    re.compile(r"\bprivate[_\- ]key\b", re.IGNORECASE),
    re.compile(r"\bpin\b(?!\s*(?:it|ned|ning))", re.IGNORECASE),
    re.compile(r"\b(?:2fa|otp|mfa|one[_\- ]time[_\- ]code)\b", re.IGNORECASE),
)


def is_credential_prompt(message: Optional[str], schema: Any = None) -> bool:
    """True if this prompt is asking for a secret the model does not hold.

    Checks the server's wording and any field names in its requested schema — a
    prompt whose message is bland ("Enter value:") but whose schema field is
    ``password`` is still a credential request.
    """
    haystack = [message or ""]
    if isinstance(schema, dict):
        props = schema.get("properties")
        if isinstance(props, dict):
            haystack.extend(str(k) for k in props)
        # A title or description can carry the real ask too.
        for key in ("title", "description"):
            value = schema.get(key)
            if isinstance(value, str):
                haystack.append(value)
    return any(p.search(text) for text in haystack for p in _CREDENTIAL_PATTERNS)


def attribute(server: Optional[str], message: Optional[str]) -> str:
    """Render a prompt as the *server's* question, never as JARVIS's.

    Every surface that shows an elicited prompt to a human goes through this, so
    the provenance cannot be lost by one renderer forgetting it.
    """
    who = server or "an unidentified server"
    text = (message or "").strip() or "(no question text)"
    return f"The MCP server {who!r} is asking: {text}"


def decide(
    message: Optional[str],
    *,
    mode: str,
    schema: Any = None,
    proposed_answer: Any = None,
    model_requests_human: bool = False,
) -> PromptDisposition:
    """Decide who answers this prompt.

    ``model_requests_human`` is the model's voluntary escalation. It can only
    raise: setting it forces a human, and leaving it false never prevents one.
    """
    # Boundary first, before any mode can speak. Even allow_all does not get to
    # hand a password prompt to a model that has no password to give.
    if is_credential_prompt(message, schema):
        return PromptDisposition.HUMAN

    # The model may always escalate; it can never de-escalate below what follows.
    if model_requests_human:
        return PromptDisposition.HUMAN

    if mode == "ask_all":
        return PromptDisposition.HUMAN
    if mode == "allow_all":
        return PromptDisposition.ROOT

    # "smart" — the same classify() that gates tool calls, run over the server's
    # question and the answer the model wants to give. An unrecognized mode
    # lands here too, matching ConfirmationManager.should_confirm: one config
    # value must not mean different things in two places, and the config write
    # path already validates it. smart is still classify()-gated, so the
    # fallback is a judged decision rather than a blind allow.
    level = classify(None, None, {"prompt": message or "", "answer": proposed_answer})
    return (
        PromptDisposition.HUMAN if level >= ThreatLevel.ELEVATED else PromptDisposition.ROOT
    )


def describe(signal: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """Turn a dispatch ``NEEDS_ACTION`` payload into a decided, renderable form.

    Returns the disposition alongside the attributed text, so a caller neither
    re-derives the policy nor has to remember to attribute the question.
    """
    server = signal.get("server")
    message = signal.get("message")
    schema = signal.get("schema")
    disposition = decide(message, mode=mode, schema=schema)
    return {
        "pid": signal.get("pid"),
        "server": server,
        "message": message,
        "schema": schema,
        "disposition": disposition.value,
        "prompt_text": attribute(server, message),
        "credential": is_credential_prompt(message, schema),
        # Always true for an elicited prompt: the text came from the server.
        "untrusted": True,
    }
