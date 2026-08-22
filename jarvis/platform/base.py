"""Abstract base for platform-specific operations."""

from __future__ import annotations

import asyncio
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional


class BasePlatform(ABC):
    """Interface that each OS backend implements."""

    # -- Paths ---------------------------------------------------------------

    @abstractmethod
    def config_dir(self) -> Path:
        """Return the user config directory (e.g. ~/.config/jarvis)."""

    @abstractmethod
    def data_dir(self) -> Path:
        """Return the user data directory (e.g. ~/.local/share/jarvis)."""

    # -- IPC -----------------------------------------------------------------

    @abstractmethod
    async def create_ipc_server(
        self,
        path: str,
        client_handler: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Any],
    ) -> asyncio.AbstractServer:
        """Create an IPC server at *path* and return the ``asyncio.Server``."""

    @abstractmethod
    def ipc_connect(self, path: str) -> Any:
        """Return a connected socket to the IPC endpoint at *path*."""

    @abstractmethod
    def ipc_cleanup(self, path: str) -> None:
        """Remove the IPC endpoint file/resource after shutdown."""

    @abstractmethod
    def ipc_secure(self, path: str) -> None:
        """Apply restrictive permissions to the IPC endpoint."""

    @abstractmethod
    def ipc_verify_owner(self, path: str) -> bool:
        """Return True if the IPC endpoint is owned by the current user."""

    @abstractmethod
    async def ipc_verify_peer(self, reader: Any, writer: Any) -> bool:
        """Return True if the connecting peer is the current user.

        Accept-time check — call and check the result before any line from
        *reader* reaches ``inject_user_input`` or a confirmation/shutdown
        handler. Async because some backends (Windows) must read a
        credential line off the wire; others (Linux/macOS) check
        synchronously via the socket and ignore *reader* entirely.

        Linux: ``SO_PEERCRED``. macOS: ``LOCAL_PEERCRED``. Windows: a
        per-startup token sent as the connection's first line (interim —
        see windows.py for why this isn't yet a true peer-credential check).
        This is the real access-control boundary on platforms (Windows)
        where the IPC transport has no filesystem permissions to rely on —
        see Project-JARVIS #168.
        """

    def system_ipc_candidates(self) -> list[str]:
        """Well-known system-wide IPC endpoint paths to probe, if any.

        Only meaningful on platforms with a shared filesystem-namespace
        default location (Linux's ``/run/jarvis``). Empty on platforms
        where no such convention exists, so callers stop guessing a
        Linux-only path.
        """
        return []

    # -- Sidecar / privileged-helper resolution -------------------------------

    def sidecar_search_dirs(self) -> list[Path]:
        """Per-OS default install directories to search for sidecar binaries."""
        return []

    def resolve_sidecar(
        self, name: str, config_override: Optional[str] = None
    ) -> Optional[str]:
        """Resolve a sidecar binary: config override -> PATH -> per-OS defaults.

        Returns the absolute path if found, else ``None``. Centralizing this
        means "not found" errors can print the real per-OS search path
        instead of a bare binary name.
        """
        if config_override:
            override_path = Path(config_override)
            if override_path.is_file():
                return str(override_path)

        found = shutil.which(name)
        if found:
            return found

        for directory in self.sidecar_search_dirs():
            for candidate in (directory / name, directory / f"{name}.exe"):
                if candidate.is_file():
                    return str(candidate)
        return None

    # -- Privilege elevation ---------------------------------------------------

    @abstractmethod
    def privileged_prefixes(self) -> tuple[str, ...]:
        """Command prefixes that require elevation on this OS.

        Fed into the TLA gate as a floor (``jarvis/core/threat_level.py``)
        rather than used for elevation directly — see Project-JARVIS #208.
        """

    # -- Notifications -------------------------------------------------------

    def has_desktop_notifications(self) -> bool:
        """Return True if desktop notifications are available.

        JARVIS_DISABLE_NOTIFICATIONS wins over backend detection on every
        platform — a headless or test environment must be able to keep the
        desktop untouched no matter what is installed (#174).
        """
        if os.environ.get("JARVIS_DISABLE_NOTIFICATIONS", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            return False
        return self._detect_desktop_notifications()

    @abstractmethod
    def _detect_desktop_notifications(self) -> bool:
        """Return True if this OS has a usable notification backend."""

    @abstractmethod
    async def send_desktop_notification(
        self,
        title: str,
        body: str,
        timeout_ms: int,
    ) -> Optional[str]:
        """Show a desktop notification. Return the chosen action or None."""

    # -- Service control -----------------------------------------------------

    @abstractmethod
    def try_start_service(self, name: str, base_url: str) -> bool:
        """Attempt to start a system service by name. Return True if it came up."""

    # -- Signals -------------------------------------------------------------

    def install_signal_handlers(
        self,
        loop: asyncio.AbstractEventLoop,
        stop_callback: Callable[[], None],
    ) -> None:
        """Register graceful-stop handlers for SIGTERM/SIGINT."""
        import signal

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, stop_callback)
            except (ValueError, OSError, NotImplementedError):
                pass
