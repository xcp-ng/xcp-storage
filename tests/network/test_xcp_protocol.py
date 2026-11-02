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

import struct
from unittest.mock import patch

import pytest

from xcp_storage.network.protocol import Protocol, ProtocolError
from xcp_storage.network.protocol.xcp import XcpProtocol
from xcp_storage.network.socket import SocketDisconnectedError, SocketPair

from xcp_storage.typing import Final

# ==============================================================================

class TestXcpProtocolSeq:
    @pytest.mark.parametrize(("seq", "expected_next_seq"), [
        (0, 1),
        (1, 2),
        (XcpProtocol.MAX_SEQ - 1, XcpProtocol.MAX_SEQ),
        (XcpProtocol.MAX_SEQ, 1)
    ])
    def test_next(self, seq: int, expected_next_seq: int) -> None:
        assert XcpProtocol().get_next_packet_seq(seq) == expected_next_seq

    def test_bounds(self) -> None:
        protocol = XcpProtocol()

        seq = 0
        for _ in range(2 * XcpProtocol.MAX_SEQ):
            seq = protocol.get_next_packet_seq(seq)
            assert 1 <= seq <= XcpProtocol.MAX_SEQ

# ------------------------------------------------------------------------------

TEST_DEFAULT_SEQ: Final = 7

# ------------------------------------------------------------------------------

def build_packet_header(
    *,
    magic: bytes = XcpProtocol.HEADER_MAGIC,
    version: int = XcpProtocol.VERSION,
    message_type: int = Protocol.MessageType.REQUEST,
    seq: int = TEST_DEFAULT_SEQ,
    payload_size: int = 0
) -> bytes:
    return struct.pack(XcpProtocol.HEADER_FORMAT, magic, version, message_type, 0, seq, payload_size, 0)

class TestXcpPacket:
    @pytest.mark.parametrize(("header", "message"), [
        (build_packet_header(magic=b"@BAD"), "Invalid magic value!"),
        (build_packet_header(version=XcpProtocol.VERSION + 1), "Invalid protocol version!"),
        (build_packet_header(message_type=99), "Invalid message type: `99`."),
        (build_packet_header(payload_size=XcpProtocol.MAX_PACKET_SIZE), "Packet is too large!")
    ])
    def test_invalid_header(self, header: bytes, message: str) -> None:
        with pytest.raises(ProtocolError, match=message) as exc_info:
            XcpProtocol.Packet.from_header(header)
        assert exc_info.value.seq == TEST_DEFAULT_SEQ

    def test_header_encode_decode(self) -> None:
        payload = b"payload"

        packet = XcpProtocol().create_packet(Protocol.MessageType.RESPONSE, TEST_DEFAULT_SEQ, payload)
        encoded = packet.encode()
        assert len(encoded) == XcpProtocol.HEADER_SIZE + len(payload)

        decoded = XcpProtocol.Packet.from_header(encoded[:XcpProtocol.HEADER_SIZE])
        assert decoded.message_type == Protocol.MessageType.RESPONSE
        assert decoded.seq == TEST_DEFAULT_SEQ
        assert decoded.payload_size == len(payload)

    def test_too_large_packet(self) -> None:
        payload = b"1234"
        with patch.object(XcpProtocol, "MAX_PACKET_SIZE", XcpProtocol.HEADER_SIZE + len(payload) - 1), \
            pytest.raises(ProtocolError, match="Packet is too large!"):
            XcpProtocol().create_packet(Protocol.MessageType.REQUEST, TEST_DEFAULT_SEQ, payload)

    def test_incompatible_payload_size(self) -> None:
        packet = XcpProtocol.Packet.from_header(build_packet_header(payload_size=3))
        with pytest.raises(ProtocolError, match="Incompatible payload size.") as exc_info:
            packet.set_payload(b"12")
        assert exc_info.value.seq == TEST_DEFAULT_SEQ

# ------------------------------------------------------------------------------

class TestXcpProtocolReceive:
    def test_receive(self, socket_pair: SocketPair) -> None:
        payload = b"Bonjour !"

        protocol = XcpProtocol()
        sock_sender, sock_receiver = socket_pair

        protocol.send_packet(
            sock_sender,
            protocol.create_packet(Protocol.MessageType.REQUEST, TEST_DEFAULT_SEQ, payload)
        )
        packet = protocol.receive_packet(sock_receiver, (Protocol.MessageType.REQUEST, ))

        assert packet.message_type == Protocol.MessageType.REQUEST
        assert packet.seq == TEST_DEFAULT_SEQ
        assert packet.payload == payload

    def test_unexpected_message_type(self, socket_pair: SocketPair) -> None:
        protocol = XcpProtocol()
        sock_sender, sock_receiver = socket_pair

        protocol.send_packet(sock_sender, protocol.create_packet(Protocol.MessageType.CONNECT, TEST_DEFAULT_SEQ))
        with pytest.raises(ProtocolError, match="Unexpected message type: CONNECT.") as exc_info:
            protocol.receive_packet(sock_receiver, (Protocol.MessageType.REQUEST, ))
        assert exc_info.value.seq == TEST_DEFAULT_SEQ

    def test_truncated_packet(self, socket_pair: SocketPair) -> None:
        sock_sender, sock_receiver = socket_pair

        sock_sender.sendall(build_packet_header(payload_size=10) + b"short")
        sock_sender.close()

        with pytest.raises(SocketDisconnectedError, match="Not enough data received."):
            XcpProtocol().receive_packet(sock_receiver, (Protocol.MessageType.REQUEST, ))
