"""
Interactive TUI frontend for JARVIS (Textual-based).

This is the OpenClaw-style chat surface: a session sidebar, a scrollable
chat log, an input box, and a status line, all in the terminal.  It is
a *frontend* — it drives the same ``Jarvis`` engine used by ``jarvis chat``
and ``jarvis run``.

Install with:
    pip install "jarvis-ai[tui]"

Launch with:
    jarvis tui

Design notes:
  * The TUI owns stdin.  ``Jarvis(tui_mode=True)`` skips the stdin event
    source; user input is fed in via ``events.inject_user_input()``.
  * Output is rendered by registering a callback on ``output_manager``.
  * Sessions are driven directly through ``SessionManager`` — no slash
    commands required (though typed ``/new``, ``/switch`` etc. still work
    via the existing handlers in ``main.py``).
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import JarvisTUI, run_tui

__all__ = ["JarvisTUI", "run_tui"]


def __getattr__(name: str) -> Any:
    """Pull in the Textual app only when it is actually asked for.

    ``input_helpers`` and ``slash_commands_doc`` are plain Python; importing
    them must not require the optional ``[tui]`` extra.  ``jarvis tui`` still
    gets the same ImportError (and the same install hint) from ``cli.py``.
    """
    if name in __all__:
        from . import app

        return getattr(app, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
