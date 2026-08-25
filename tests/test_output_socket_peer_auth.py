"""Output socket must authenticate its peer at accept time (jarvis/runtime/io.py).

The input and GUI handlers call ``platform.ipc_verify_peer`` before trusting a
connection; the output handler did not, so on Windows (loopback TCP) any local
process could subscribe to all daemon output. This mirrors the sibling
handlers' peer-rejection contract for the output socket.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from jarvis.runtime import io as runtime_io


class _RecordingList(list):
    """A list that remembers everything ever appended, even after removal."""

    def __init__(self):
        super().__init__()
        self.ever_appended = []

    def append(self, item):
        self.ever_appended.append(item)
        super().append(item)


def _make_app():
    return SimpleNamespace(_output_clients=_RecordingList(), _running=True)


def _make_writer():
    writer = Mock()
    writer.wait_closed = AsyncMock()
    return writer


@pytest.mark.unit
class TestOutputConnectionPeerAuth:
    @pytest.mark.asyncio
    async def test_unverified_peer_is_not_subscribed(self):
        app = _make_app()
        reader = Mock()
        reader.read = AsyncMock(return_value=b"")
        writer = _make_writer()

        with patch.object(
            runtime_io.platform,
            "ipc_verify_peer",
            new=AsyncMock(return_value=False),
        ):
            await runtime_io.handle_output_connection(app, Mock(), reader, writer)

        # Never appended at all — the accept path bailed before subscribing.
        assert writer not in app._output_clients.ever_appended
        assert app._output_clients == []
        writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_verified_peer_is_subscribed(self):
        app = _make_app()
        reader = Mock()
        reader.read = AsyncMock(return_value=b"")
        writer = _make_writer()

        with patch.object(
            runtime_io.platform,
            "ipc_verify_peer",
            new=AsyncMock(return_value=True),
        ):
            await runtime_io.handle_output_connection(app, Mock(), reader, writer)

        # The accept path ran: it was appended (then removed on EOF disconnect).
        assert writer in app._output_clients.ever_appended
