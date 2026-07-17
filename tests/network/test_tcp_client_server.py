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
import threading

import pytest

from xcp_storage.network.socket import SocketDisconnectedError
from xcp_storage.network.tcp_client import TcpClient, TcpClientError
from xcp_storage.network.tcp_server import TcpServer

from xcp_storage.typing import (
    Final,
    Generator,
    override,
)

# ==============================================================================

@pytest.fixture
def tcp_server(request: pytest.FixtureRequest) -> Generator[TcpServer, None, None]:
    server_class = request.param
    server = server_class("127.0.0.1", 0)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    server.wait_for_startup()

    yield server

    server.stop()
    server_thread.join(timeout=2.0)

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

class TestTcpClientServer:
    CLIENT_TIMEOUT: Final = 5.0

    def test_client_connect_timeout_failure(self) -> None:
        tcp_client = TcpClient("127.0.0.1", port=59999, client_timeout=0.5)
        with pytest.raises(TcpClientError, match="Unable to connect to server."):
            tcp_client.connect()
        assert not tcp_client.socket

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_client_server_echo(self, tcp_server: TcpServer) -> None:
        payload = b"Hello World!"
        with TcpClient(tcp_server.address, tcp_server.port, client_timeout=self.CLIENT_TIMEOUT) as tcp_client:
            assert tcp_client.connected

            tcp_client.send(payload)
            buffer = bytearray(len(payload))
            tcp_client.receive(buffer)
            assert bytes(buffer) == payload

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [EchoServer], indirect=True)
    def test_client_receive_after_close(self, tcp_server: TcpServer) -> None:
        tcp_client = TcpClient(tcp_server.address, tcp_server.port, client_timeout=self.CLIENT_TIMEOUT)
        tcp_client.connect()
        assert tcp_client.socket
        tcp_client.socket.close()

        buffer = bytearray(16)
        with pytest.raises(SocketDisconnectedError):
            tcp_client.receive(buffer)

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [RejectConnectionServer], indirect=True)
    def test_client_rejected_by_server(self, tcp_server: TcpServer) -> None:
        tcp_client = TcpClient(tcp_server.address, tcp_server.port, client_timeout=self.CLIENT_TIMEOUT)
        tcp_client.connect()

        with pytest.raises(SocketDisconnectedError):
            tcp_client.send(b"Moshimoshi?")
            buffer = bytearray(16)
            tcp_client.receive(buffer)

        assert not tcp_client.connected

    @pytest.mark.parametrize("tcp_server", [FragmentedServer], indirect=True)
    def test_client_handles_fragmented_stream(self, tcp_server: TcpServer) -> None:
        payload = b"A fragmented message."
        with TcpClient(tcp_server.address, tcp_server.port, client_timeout=self.CLIENT_TIMEOUT) as tcp_client:
            tcp_client.send(payload)
            buffer = bytearray(len(payload))
            tcp_client.receive(buffer)
            assert bytes(buffer) == payload

    @pytest.mark.parametrize("tcp_server", [SingleRequestServer], indirect=True)
    def test_server_single_request(self, tcp_server: TcpServer) -> None:
        expected_message = b"ACK"
        with TcpClient(tcp_server.address, tcp_server.port, client_timeout=self.CLIENT_TIMEOUT) as tcp_client:
            tcp_client.send(b"Ping?")
            buffer = bytearray(len(expected_message))
            tcp_client.receive(buffer)
            assert bytes(buffer) == expected_message

            with pytest.raises(SocketDisconnectedError):
                tcp_client.receive(buffer)

            assert not tcp_client.connected
