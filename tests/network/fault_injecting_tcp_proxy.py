# Copyright (C) 2026  Vates SAS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import contextlib
from enum import Enum
import threading

from xcp_storage.network.tcp_server import TcpServer
from xcp_storage.utils.asyncio import abort_stream_writer, close_stream_writer

from xcp_storage.typing import (
    Dict,
    Final,
    Optional,
    override,
)

# ==============================================================================

class FaultInjectingTcpProxyMode(Enum):
    # Forward the data both ways.
    FORWARD = "forward"
    # Close the new connections at once.
    SERVER_DOWN = "server-down"
    # Accept the new connections and never answer.
    SERVER_HUNG = "server-hung"

class _ResponseFault(Enum):
    # The response is dropped.
    LOSE = "lose"
    # The response never comes but the connection stays open.
    HANG = "hang"

class _ForwardedConnection:
    """
    Connection of a client, forwarded to the server.
    """

    def __init__(
        self, client: TcpServer.Client, server_reader: asyncio.StreamReader, server_writer: asyncio.StreamWriter
    ) -> None:
        self.client = client
        self.server_reader = server_reader
        self.server_writer = server_writer

        # Start of the current request: the data received from the client since the last response, up to the
        # `request_start_size` of the proxy, whatever its chunks.
        self.request_start_data = b""

        self.response_received = False

class FaultInjectingTcpProxy(TcpServer):
    """
    Local TCP proxy forwarding its connections to a real server, where the tests inject network failures between a
    client and this server: server down or hung (`mode`), connections dropped, response lost or hung.
    """

    # Maximum time in seconds to connect to the server.
    _CONNECT_TIMEOUT: Final = 5.0

    # Maximum time in seconds to drop the connections.
    _DROP_CONNECTIONS_TIMEOUT: Final = 5.0

    _CLIENT_READ_BUFFER_SIZE: Final = 65536

    # Default maximum size of the start of a request given to `_is_response_fault_target`: enough to recognize any
    # request.
    _DEFAULT_REQUEST_START_SIZE: Final = 256

    def __init__(self, address: str, port: int, *, request_start_size: int = _DEFAULT_REQUEST_START_SIZE) -> None:
        # No limit nor timeout on the clients: the proxy must not add its own limits.
        super().__init__("127.0.0.1", 0, max_clients=None, client_connect_timeout=None, client_idle_timeout=None)

        if request_start_size < 1:
            raise ValueError(f"Invalid request start size: `{request_start_size}`.")
        # Given by a subclass, which knows how many bytes recognize a request.
        self._request_start_size = request_start_size

        self.mode = FaultInjectingTcpProxyMode.FORWARD

        self._server_address = address
        self._server_port = port

        self._connection_count = 0
        self._lost_response_count = 0

        self._connections: Dict[TcpServer.Client, _ForwardedConnection] = {}

        # Reentrant lock: a subclass changes its own state and calls the methods of this class under the same lock.
        self._next_response_fault_lock = threading.RLock()
        self._next_response_fault: Optional[_ResponseFault] = None

    @property
    def connection_count(self) -> int:
        """
        Number of connections accepted since the start, whatever the mode.
        """

        return self._connection_count

    @property
    def lost_response_count(self) -> int:
        """
        Number of responses lost by `lose_next_response`.
        """

        return self._lost_response_count

    def drop_connections(self) -> None:
        """
        Close the current connections, both sides: the next requests of the client need a new connection.
        """

        async def drop() -> None:
            writers = [client.writer for client in self._clients]
            writers += [connection.server_writer for connection in self._connections.values()]
            for writer in writers:
                await abort_stream_writer(writer)

        assert self._event_loop, "Proxy not running."
        asyncio.run_coroutine_threadsafe(drop(), self._event_loop).result(self._DROP_CONNECTIONS_TIMEOUT)

    def lose_next_response(self) -> None:
        """
        Lose the next response of the server.
        """

        with self._next_response_fault_lock:
            self._next_response_fault = _ResponseFault.LOSE

    def hang_next_response(self) -> None:
        """
        Hang the next response of the server.
        """

        with self._next_response_fault_lock:
            self._next_response_fault = _ResponseFault.HANG

    @override
    async def _handle_client_connect(self, client: TcpServer.Client) -> bool:
        self._connection_count += 1

        if self.mode is FaultInjectingTcpProxyMode.SERVER_DOWN:
            return False
        if self.mode is FaultInjectingTcpProxyMode.SERVER_HUNG:
            await self._wait_reader_closed(client.reader)
            return False

        try:
            server_reader, server_writer = await asyncio.wait_for(
                asyncio.open_connection(self._server_address, self._server_port),
                self._CONNECT_TIMEOUT
            )
        except (asyncio.TimeoutError, OSError):
            return False

        self._connections[client] = _ForwardedConnection(client, server_reader, server_writer)
        return True

    @override
    async def _handle_client_disconnect(self, client: TcpServer.Client) -> None:
        await close_stream_writer(self._connections.pop(client).server_writer)

    @override
    async def _handle_client_request(self, client: TcpServer.Client) -> bool:
        # Forward the data both ways until the end of the connection, then return `False` to close it.
        connection = self._connections[client]

        # TODO(XCPNG-3032): Replace with create_task in python 3.7 and `_task` suffix on variables.
        request_future = asyncio.ensure_future(self._forward_requests(connection))
        response_future = asyncio.ensure_future(self._forward_responses(connection))
        try:
            await asyncio.wait([request_future, response_future], return_when=asyncio.FIRST_COMPLETED)
            for future in (request_future, response_future):
                # A forwarding fails with an `OSError` when its connection is closed meanwhile: by its peer, by
                # `drop_connections` or at the stop of the proxy. Any other exception is a bug: raised, then logged by
                # `TcpServer`.
                if future.done() and not future.cancelled():
                    exception = future.exception()
                    if exception and not isinstance(exception, OSError):
                        raise exception
        finally:
            for future in (request_future, response_future):
                future.cancel()
                # Read the error of a failed future, else asyncio logs it.
                if future.done() and not future.cancelled():
                    future.exception()
        return False

    def _is_response_fault_target(self, request_data: bytes) -> bool: # noqa: ARG002
        """
        Determine whether the response to a request triggers a simulated error.
        `request_data` is the start of this request (up to `request_start_size` bytes).
        """

        return True

    async def _forward_requests(self, connection: _ForwardedConnection) -> None:
        while True:
            data = await connection.client.reader.read(self._CLIENT_READ_BUFFER_SIZE)
            if not data:
                return

            if connection.response_received:
                connection.response_received = False
                connection.request_start_data = b""
            if len(connection.request_start_data) < self._request_start_size:
                connection.request_start_data = (connection.request_start_data + data)[:self._request_start_size]

            connection.server_writer.write(data)
            await connection.server_writer.drain()

    async def _forward_responses(self, connection: _ForwardedConnection) -> None:
        while True:
            data = await connection.server_reader.read(self._CLIENT_READ_BUFFER_SIZE)
            if not data:
                return
            connection.response_received = True

            response_fault = self._take_response_fault(connection)
            if response_fault is _ResponseFault.HANG:
                # The responses are no longer read. The event is never set: the wait only ends when this forwarding is
                # cancelled by `_handle_client_request`, once the forwarding of the requests ends (the client closes
                # the connection or it is dropped), or at the stop of the proxy.
                await asyncio.Event().wait()
                raise AssertionError("Hung response forwarded.") # pragma: no cover
            if response_fault is _ResponseFault.LOSE:
                return

            connection.client.writer.write(data)
            await connection.client.writer.drain()

    def _take_response_fault(self, connection: _ForwardedConnection) -> Optional[_ResponseFault]:
        with self._next_response_fault_lock:
            response_fault = self._next_response_fault
            if response_fault is None or not self._is_response_fault_target(connection.request_start_data):
                return None
            self._next_response_fault = None

            if response_fault is _ResponseFault.LOSE:
                self._lost_response_count += 1
            return response_fault

    @classmethod
    async def _wait_reader_closed(cls, reader: asyncio.StreamReader) -> None:
        # The data of the client is read and dropped until the end of the connection.
        with contextlib.suppress(OSError):
            while await reader.read(cls._CLIENT_READ_BUFFER_SIZE):
                pass
