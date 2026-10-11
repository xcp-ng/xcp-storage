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
import socket
import ssl
import threading
import time

import pytest

from tests.network import find_free_tcp_port
from tests.network.tls import over_plain_and_tls, TlsContexts
from xcp_storage.network.socket import (
    get_socket_port,
    SocketDisconnectedError,
    SocketError,
)
from xcp_storage.network.tcp_client import TcpClient, TcpClientError
from xcp_storage.network.tcp_server import TcpServer, TcpServerError

from xcp_storage.typing import (
    Callable,
    cast,
    Final,
    Generator,
    Optional,
    override,
)

# ==============================================================================

SERVER_STARTUP_TIMEOUT: Final = 5.0
SERVER_SHUTDOWN_TIMEOUT: Final = 5.0

SERVER_THREAD_SHUTDOWN_TIMEOUT: Final = 5.0

CLIENT_TIMEOUT: Final = 5.0

# ------------------------------------------------------------------------------

@contextlib.contextmanager
def run_threaded_server(tcp_server: TcpServer) -> Generator[TcpServer, None, None]:
    server_thread = threading.Thread(target=tcp_server.run, daemon=True)
    server_thread.start()
    try:
        assert tcp_server.wait_for_startup(timeout=SERVER_STARTUP_TIMEOUT), "Server not started."
        yield tcp_server
    finally:
        tcp_server.stop(timeout=SERVER_SHUTDOWN_TIMEOUT)
        server_thread.join(timeout=SERVER_THREAD_SHUTDOWN_TIMEOUT)
        assert not server_thread.is_alive(), "Server thread still alive."

@pytest.fixture
def tcp_server(
    request: pytest.FixtureRequest,
    ssl_contexts: Optional[TlsContexts]
) -> Generator[TcpServer, None, None]:
    server_class = request.param
    server = server_class("127.0.0.1", 0, ssl_context=ssl_contexts.server if ssl_contexts else None)
    with run_threaded_server(server) as threaded_server:
        yield threaded_server

TcpClientFactory = Callable[[], TcpClient]

@pytest.fixture
def tcp_client_factory(tcp_server: TcpServer, client_ssl_context: Optional[ssl.SSLContext]) -> TcpClientFactory:
    def factory() -> TcpClient:
        return TcpClient(
            tcp_server.address,
            tcp_server.port,
            client_timeout=CLIENT_TIMEOUT,
            ssl_context=client_ssl_context
        )
    return factory

# ------------------------------------------------------------------------------

class EchoServer(TcpServer):
    @override
    async def _handle_client_connect(self, client: TcpServer.Client) -> bool:
        return True

    @override
    async def _handle_client_disconnect(self, client: TcpServer.Client) -> None:
        pass

    @override
    async def _handle_client_request(self, client: TcpServer.Client) -> bool:
        try:
            data = await client.reader.read(1024)
            if not data:
                return False
            client.writer.write(data)
            await client.writer.drain()
            return True
        except Exception:
            return False

# ------------------------------------------------------------------------------

class RejectConnectionServer(TcpServer):
    @override
    async def _handle_client_connect(self, client: TcpServer.Client) -> bool:
        return False

    @override
    async def _handle_client_disconnect(self, client: TcpServer.Client) -> None:
        pass

    @override
    async def _handle_client_request(self, client: TcpServer.Client) -> bool:
        return False

# ------------------------------------------------------------------------------

class FragmentedServer(TcpServer):
    @override
    async def _handle_client_connect(self, client: TcpServer.Client) -> bool:
        return True

    @override
    async def _handle_client_disconnect(self, client: TcpServer.Client) -> None:
        pass

    @override
    async def _handle_client_request(self, client: TcpServer.Client) -> bool:
        data = await client.reader.read(1024)
        if not data:
            return False
        for octet in data:
            client.writer.write(bytes([octet]))
            await client.writer.drain()
            await asyncio.sleep(0.05)
        return True

# ------------------------------------------------------------------------------

class SingleRequestServer(TcpServer):
    @override
    async def _handle_client_connect(self, client: TcpServer.Client) -> bool:
        return True

    @override
    async def _handle_client_disconnect(self, client: TcpServer.Client) -> None:
        pass

    @override
    async def _handle_client_request(self, client: TcpServer.Client) -> bool:
        await client.reader.read(1024)
        client.writer.write(b"ACK")
        await client.writer.drain()
        return False

# ==============================================================================

class TestTcpClient:
    def test_del_without_init(self) -> None:
        tcp_client = TcpClient.__new__(TcpClient)
        tcp_client.__del__() # Must not raise even if `__init__` has not been called.

    def test_not_connected(self) -> None:
        tcp_client = TcpClient("127.0.0.1", port=0)
        assert not tcp_client.connected
        with pytest.raises(TcpClientError, match="Cannot send. Not connected."):
            tcp_client.send(b"")
        with pytest.raises(TcpClientError, match="Cannot receive. Not connected."):
            tcp_client.receive(bytearray())

    def test_connect_timeout_failure(self) -> None:
        client_timeout = 0.5
        tcp_client = TcpClient("127.0.0.1", port=0, client_timeout=client_timeout)
        start_time = time.monotonic()

        with pytest.raises(TcpClientError, match="Unable to connect to server."):
            tcp_client.connect()

        elapsed_time = time.monotonic() - start_time
        assert elapsed_time >= client_timeout
        assert elapsed_time < 1.0
        assert not tcp_client.socket

    def test_connect_zero_timeout(self) -> None:
        tcp_client = TcpClient("127.0.0.1", port=0, client_timeout=CLIENT_TIMEOUT)
        start_time = time.monotonic()

        with pytest.raises(TcpClientError, match="Unable to connect to server."):
            tcp_client.connect(timeout=0.0)

        elapsed_time = time.monotonic() - start_time
        assert elapsed_time < 1.0
        assert not tcp_client.socket

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_connect_is_idempotent(self, tcp_client_factory: TcpClientFactory) -> None:
        with tcp_client_factory() as tcp_client:
            assert tcp_client.connected

            client_socket = tcp_client.socket
            assert client_socket

            tcp_client.connect()
            assert tcp_client.socket is client_socket

            tcp_client.disconnect()
            assert not tcp_client.connected

    def test_disconnect_is_idempotent(self) -> None:
        tcp_client = TcpClient("127.0.0.1", port=0)

        tcp_client.disconnect()
        assert not tcp_client.connected
        tcp_client.disconnect()
        assert not tcp_client.connected

    def test_connect_retries_until_server_is_up(self) -> None:
        tcp_port = find_free_tcp_port()
        tcp_server = EchoServer("127.0.0.1", tcp_port)

        def run() -> None:
            time.sleep(0.5)
            with run_threaded_server(tcp_server):
                time.sleep(3.0)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        try:
            with TcpClient("127.0.0.1", tcp_port, client_timeout=CLIENT_TIMEOUT) as tcp_client:
                assert tcp_client.connected
        finally:
            tcp_server.stop(timeout=SERVER_SHUTDOWN_TIMEOUT)
            thread.join(timeout=SERVER_THREAD_SHUTDOWN_TIMEOUT)

    @pytest.mark.parametrize("ssl_contexts", [True], indirect=True, ids=["tls"])
    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_connect_with_untrusted_certificate(self, tcp_server: TcpServer) -> None:
        # The default context only trusts the system CAs: the server self-signed certificate must be rejected.
        tcp_client = TcpClient(
            tcp_server.address,
            tcp_server.port,
            ssl_context=ssl.create_default_context(),
            client_timeout=CLIENT_TIMEOUT
        )
        with pytest.raises(TcpClientError, match="Unable to connect to server."):
            tcp_client.connect()

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_nested_with(self, tcp_server: TcpServer) -> None:
        tcp_client = TcpClient(tcp_server.address, tcp_server.port, client_timeout=CLIENT_TIMEOUT)
        with tcp_client:
            with tcp_client:
                assert tcp_client.connected
            assert tcp_client.connected
        assert not tcp_client.connected

# ------------------------------------------------------------------------------

class TestTcpServer:
    def test_running_on_fixed_port(self) -> None:
        tcp_port = find_free_tcp_port()
        tcp_server = EchoServer("127.0.0.1", tcp_port)
        assert tcp_server.port == tcp_port
        with run_threaded_server(tcp_server):
            assert tcp_server.port == tcp_port

    def test_run_twice(self) -> None:
        with run_threaded_server(EchoServer("127.0.0.1", 0)) as threaded_server, \
            pytest.raises(TcpServerError, match="Server is already running."):
                threaded_server.run()

    def test_stop_just_after_startup(self) -> None:
        # Ensure we don't have a regression/race condition somewhere.
        for _ in range(100):
            with run_threaded_server(EchoServer("127.0.0.1", 0)):
                pass

    def test_startup_on_used_port(self) -> None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            tcp_server = EchoServer("127.0.0.1", cast(int, get_socket_port(sock)))
            with pytest.raises(SocketError, match="Failed to bind server sock."):
                tcp_server.run()

        assert not tcp_server.wait_for_startup(timeout=SERVER_STARTUP_TIMEOUT)
        tcp_server.wait_for_shutdown()

# ------------------------------------------------------------------------------

@over_plain_and_tls
class TestTcpClientServer:
    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_client_server_echo(self, tcp_client_factory: TcpClientFactory) -> None:
        payload = b"Hello World!"
        with tcp_client_factory() as tcp_client:
            assert tcp_client.connected

            tcp_client.send(payload)
            buffer = bytearray(len(payload))
            tcp_client.receive(buffer)
            assert bytes(buffer) == payload

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_client_server_echo_with_fixed_size(self, tcp_client_factory: TcpClientFactory) -> None:
        payload = b"Hello World!"
        part_size = 5
        payload_part = payload[:part_size]

        with tcp_client_factory() as tcp_client:
            assert tcp_client.connected

            tcp_client.send(payload, part_size)
            buffer = bytearray(16)
            tcp_client.receive(buffer, part_size)
            assert bytes(buffer[:part_size]) == payload_part
            assert bytes(buffer[part_size:]) == bytes(len(buffer) - part_size)

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_client_receive_after_close(self, tcp_client_factory: TcpClientFactory) -> None:
        tcp_client = tcp_client_factory()
        tcp_client.connect()
        assert tcp_client.socket
        tcp_client.socket.close()

        buffer = bytearray(16)
        with pytest.raises(SocketDisconnectedError):
            tcp_client.receive(buffer)

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_client_delete_to_close(self, tcp_client_factory: TcpClientFactory) -> None:
        tcp_client = tcp_client_factory()
        tcp_client.connect()
        assert tcp_client.connected

        tcp_client.__del__()
        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [RejectConnectionServer], indirect=True)
    def test_client_rejected_by_server(self, tcp_client_factory: TcpClientFactory) -> None:
        tcp_client = tcp_client_factory()
        tcp_client.connect()

        buffer = bytearray(16)
        with pytest.raises(SocketDisconnectedError):
            tcp_client.receive(buffer)

        with pytest.raises(TcpClientError, match="Cannot send. Not connected."):
            tcp_client.send(b"Moshimoshi?")

        with pytest.raises(TcpClientError, match="Cannot receive. Not connected."):
            tcp_client.receive(buffer)

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [RejectConnectionServer], indirect=True)
    def test_client_send_to_closed_peer(self, tcp_client_factory: TcpClientFactory) -> None:
        tcp_client = tcp_client_factory()
        tcp_client.connect()

        # Wait for the server to close its side. Otherwise all the sends below could complete
        # before the server has handled the connection, and nothing would fail.
        assert tcp_client.socket
        assert tcp_client.socket.wait_readable(timeout=2.0)

        deadline = time.monotonic() + 1.0
        with pytest.raises(SocketDisconnectedError, match="Unable to send data."):
            while time.monotonic() < deadline:
                tcp_client.send(b"Moshimoshi?")

        with pytest.raises(TcpClientError, match="Cannot send. Not connected."):
            tcp_client.send(b"Moshimoshi?")

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [FragmentedServer], indirect=True)
    def test_client_handles_fragmented_stream(self, tcp_client_factory: TcpClientFactory) -> None:
        payload = b"A fragmented message."
        with tcp_client_factory() as tcp_client:
            tcp_client.send(payload)
            buffer = bytearray(len(payload))
            tcp_client.receive(buffer)
            assert bytes(buffer) == payload

    @pytest.mark.parametrize("tcp_server", [SingleRequestServer], indirect=True)
    def test_server_single_request(self, tcp_client_factory: TcpClientFactory) -> None:
        expected_message = b"ACK"
        with tcp_client_factory() as tcp_client:
            tcp_client.send(b"Ping?")
            buffer = bytearray(len(expected_message))
            tcp_client.receive(buffer)
            assert bytes(buffer) == expected_message

            with pytest.raises(SocketDisconnectedError):
                tcp_client.receive(buffer)

            assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_multiple_server_clients(self, tcp_client_factory: TcpClientFactory) -> None:
        with contextlib.ExitStack() as stack:
            tcp_clients = [stack.enter_context(tcp_client_factory()) for _ in range(5)]
            messages = [f"client-{i}".encode() for i in range(len(tcp_clients))]

            for tcp_client, message in zip(tcp_clients, messages):
                tcp_client.send(message)
            for tcp_client, message in zip(tcp_clients, messages):
                buffer = bytearray(len(message))
                tcp_client.receive(buffer)
                assert bytes(buffer) == message

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_server_stop_with_multiple_clients(
        self, tcp_server: TcpServer, tcp_client_factory: TcpClientFactory
    ) -> None:
        with contextlib.ExitStack() as stack:
            tcp_clients = [stack.enter_context(tcp_client_factory()) for _ in range(5)]

            message = b"ping"
            for tcp_client in tcp_clients:
                tcp_client.send(message)
                buffer = bytearray(len(message))
                tcp_client.receive(buffer)
                assert bytes(buffer) == message

            assert tcp_server.stop(timeout=SERVER_SHUTDOWN_TIMEOUT)

            for tcp_client in tcp_clients:
                with pytest.raises(SocketDisconnectedError):
                    tcp_client.send(message)
                    tcp_client.receive(bytearray(len(message)))

            for tcp_client in tcp_clients:
                assert not tcp_client.connected
