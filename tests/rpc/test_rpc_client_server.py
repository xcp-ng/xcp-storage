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
from xcp_storage.network.protocol.xcp import XcpProtocol
from xcp_storage.network.tcp_client import TcpClientError
from xcp_storage.rpc.client import RpcApiClient
from xcp_storage.rpc.server import RpcApiServer
from xcp_storage.utils.json.rpc import JsonRpcRequestError

from xcp_storage.typing import (
    Final,
    List,
    Sequence,
    Tuple,
)

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

    def test_rpc_packet_last_sequences(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)

        protocol = rpc_client._protocol # noqa: SLF001
        send_packet = protocol.send_packet
        receive_packet = protocol.receive_packet
        request_info: List[Tuple[Protocol.MessageType, int]] = []
        response_info: List[Tuple[Protocol.MessageType, int]] = []

        def track_and_send(sock: socket.socket, packet: Protocol.Packet) -> None:
            request_info.append((packet.message_type, packet.seq))
            send_packet(sock, packet)

        def track_and_receive(sock: socket.socket, message_types: Sequence[Protocol.MessageType]) -> Protocol.Packet:
            packet = receive_packet(sock, message_types)
            response_info.append((packet.message_type, packet.seq))
            return packet

        rpc_client._seq = XcpProtocol.MAX_SEQ - 2 # noqa: SLF001

        with patch.object(protocol, "send_packet", side_effect=track_and_send), \
                patch.object(protocol, "receive_packet", side_effect=track_and_receive):
            for i in range(5):
                message = f"message-{i}"
                assert rpc_client.call("echo.echo", params={"message": message}) == message

        assert rpc_client.connected
        assert request_info == [
            (Protocol.MessageType.CONNECT, XcpProtocol.MAX_SEQ - 1),
            (Protocol.MessageType.REQUEST, XcpProtocol.MAX_SEQ),
            (Protocol.MessageType.REQUEST, 1),
            (Protocol.MessageType.REQUEST, 2),
            (Protocol.MessageType.REQUEST, 3),
            (Protocol.MessageType.REQUEST, 4)
        ]
        assert response_info == [
            (Protocol.MessageType.RESPONSE, XcpProtocol.MAX_SEQ),
            (Protocol.MessageType.RESPONSE, 1),
            (Protocol.MessageType.RESPONSE, 2),
            (Protocol.MessageType.RESPONSE, 3),
            (Protocol.MessageType.RESPONSE, 4)
        ]
        assert rpc_client._seq == 4 # noqa: SLF001

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
            rpc_client.call("echo.defer_echo", params={"message": "bonjour", "delay": 2.0})

        assert not rpc_client.connected
