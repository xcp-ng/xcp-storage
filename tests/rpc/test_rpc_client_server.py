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

import socket
from unittest.mock import patch

import pytest

from xcp_storage.network.protocol import Protocol, ProtocolError
from xcp_storage.network.tcp_client import TcpClientError
from xcp_storage.rpc.client import RpcApiClient
from xcp_storage.rpc.server import RpcApiServer
from xcp_storage.utils.json.rpc import JsonRpcRequestError

from xcp_storage.typing import Final

# ==============================================================================

class TestRpcClientServer:
    CLIENT_TIMEOUT: Final = 1.0

    def test_invalid_method(self, rpc_server: RpcApiServer) -> None:
        def non_rpc_function() -> None:
            pass

        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port)
        with pytest.raises(JsonRpcRequestError, match="Method is not marked as RPC."):
            rpc_client.call_api(non_rpc_function)

    def test_connect_with_unreachable_server(self) -> None:
        rpc_client = RpcApiClient("10.255.255.1", 9999, client_timeout=self.CLIENT_TIMEOUT)
        with pytest.raises(TcpClientError, match="Unable to connect to server."):
            rpc_client.connect()

    def test_retry_call_on_socket_disconnect(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)

        rpc_client.connect()
        assert rpc_client.connected

        tpc_socket = rpc_client._tcp_client.socket # noqa: SLF001
        assert tpc_socket
        tpc_socket.close()

        message = "Bonjour !"
        response = rpc_client.call("echo.echo", params={"message": message})
        assert response == message
        assert rpc_client.connected

    def test_corrupted_client_packet(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)

        def side_effect_send(sock: socket.socket, _packet: Protocol.Packet) -> None:
            sock.sendall(b"BBBBBBBBBBBBB")

        with patch.object(rpc_client._protocol, "send_packet", side_effect=side_effect_send), \
            pytest.raises(ProtocolError, match="Invalid sequence detected. Current=16962, expected=2."): # noqa: SLF001
            rpc_client.call("echo.echo", params={"message": "ignored"})

        assert not rpc_client.connected

    def test_server_stops_during_call(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)
        rpc_client.connect()
        assert rpc_client.connected

        send_packet = rpc_client._protocol.send_packet # noqa: SLF001

        def send_packet_and_stop(sock: socket.socket, packet: Protocol.Packet) -> None:
            send_packet(sock, packet)
            rpc_server.stop()

        with patch.object(rpc_client._protocol, "send_packet", side_effect=send_packet_and_stop), \
            pytest.raises(TcpClientError, match="Unable to connect to server."): # noqa: SLF001
            rpc_client.call("echo.defer_echo", params={"message": "bonjour", "delay": 100.0})

        assert not rpc_client.connected
