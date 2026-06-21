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

import errno
import ipaddress
import socket
from unittest.mock import (
    call,
    MagicMock,
    patch,
)

import pytest

from xcp_storage.network.socket import (
    _SERVER_BACKLOG,
    create_client_sock,
    create_server_sock,
    format_address,
    get_ip_address,
    get_socket_family_str,
    Socket,
    socket_receive,
    socket_send,
    SocketDisconnectedError,
    SocketError,
    SocketTimeoutError,
)

from xcp_storage.typing import Final, Optional

# ==============================================================================

class TestAddress:
    def test_get_ip_address_with_localhost(self) -> None:
        assert get_ip_address("127.0.0.1") == ipaddress.IPv4Address("127.0.0.1")
        assert get_ip_address("::1") == ipaddress.IPv6Address("::1")

    @patch("socket.getaddrinfo")
    def test_get_ip_address_dns_resolution(self, mock_getaddrinfo: MagicMock) -> None:
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 80))]
        ip_address = get_ip_address("localhost", ip_version=4)
        assert ip_address == ipaddress.IPv4Address("192.168.1.1")
        mock_getaddrinfo.assert_called_once_with("localhost", 80, socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)

    @patch("socket.getaddrinfo")
    def test_get_ip_address_errors(self, mock_getaddrinfo: MagicMock) -> None:
        with pytest.raises(SocketError, match="Unknown IP version."):
            get_ip_address("localhost", ip_version=67)

        mock_getaddrinfo.side_effect = socket.gaierror("Internal error.")
        with pytest.raises(SocketError, match="Cannot resolve IP."):
            get_ip_address("localhost")

        mock_getaddrinfo.side_effect = None
        mock_getaddrinfo.return_value = []
        with pytest.raises(SocketError, match="Cannot resolve IP: no valid address."):
            get_ip_address("localhost")

    def test_format_address_with_localhost(self) -> None:
        family, bind = format_address("127.0.0.1", 8080)
        assert family == socket.AF_INET
        assert bind == ("127.0.0.1", 8080)

        family, bind = format_address("::1", 8080)
        assert family == socket.AF_INET6
        assert bind == ("::1", 8080, 0, 0)

    def test_format_address_no_hostname(self) -> None:
        with pytest.raises(SocketError, match="No hostname/IP."):
            format_address("", 8080)

# ------------------------------------------------------------------------------

@patch("socket.socket")
class TestSocketCreate:
    @pytest.mark.parametrize("reuse_address", (True, False))
    @pytest.mark.parametrize("keep_alive", (True, False))
    @pytest.mark.parametrize("timeout", (5.0, 0.0, None))
    def test_create_server_sock(
        self,
        mock_socket_class: MagicMock,
        *,
        reuse_address: bool,
        keep_alive: bool,
        timeout: Optional[float]
    ) -> None:
        mock_socket = mock_socket_class.return_value
        server_socket = create_server_sock(
            "127.0.0.1",
            1234,
            reuse_address=reuse_address,
            keep_alive=keep_alive,
            timeout=timeout
        )
        assert server_socket == mock_socket

        mock_socket.bind.assert_called_once_with(("127.0.0.1", 1234))
        mock_socket.listen.assert_called_once_with(_SERVER_BACKLOG)

        assert reuse_address == (call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) in mock_socket.setsockopt.mock_calls)
        assert keep_alive == (call(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in mock_socket.setsockopt.mock_calls)

        if timeout is not None:
            mock_socket.settimeout.assert_called_once_with(timeout)
        else:
            mock_socket.settimeout.assert_not_called()

    def test_create_server_sock_bind_fail(self, mock_socket_class: MagicMock) -> None:
        mock_socket = mock_socket_class.return_value
        mock_socket.bind.side_effect = OSError("Internal error.")

        with pytest.raises(SocketError, match="Failed to bind server sock."):
            create_server_sock("127.0.0.1", 8888)

        mock_socket.close.assert_called_once()

    @pytest.mark.parametrize("reuse_address", (True, False))
    @pytest.mark.parametrize("keep_alive", (True, False))
    @pytest.mark.parametrize("timeout", (5.0, 0.0, None))
    def test_create_client_sock(
        self,
        mock_socket_class: MagicMock,
        *,
        reuse_address: bool,
        keep_alive: bool,
        timeout: Optional[float]
    ) -> None:
        mock_socket = mock_socket_class.return_value
        client_socket = create_client_sock(
            "127.0.0.1",
            1234,
            reuse_address=reuse_address,
            keep_alive=keep_alive,
            timeout=timeout
        )
        assert client_socket == mock_socket

        mock_socket.connect.assert_called_with(("127.0.0.1", 1234))

        assert reuse_address == (call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) in mock_socket.setsockopt.mock_calls)
        assert keep_alive == (call(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in mock_socket.setsockopt.mock_calls)

        if timeout is not None:
            mock_socket.settimeout.assert_called_once_with(timeout)
        else:
            mock_socket.settimeout.assert_not_called()

        if timeout is not None:
            mock_socket.settimeout.assert_called_once_with(timeout)
        else:
            mock_socket.settimeout.assert_not_called()

    def test_create_client_sock_connect_fail(self, mock_socket_class: MagicMock) -> None:
        mock_socket = mock_socket_class.return_value
        mock_socket.connect.side_effect = OSError("Internal error.")

        with pytest.raises(SocketError, match="Failed to connect client sock."):
            create_client_sock("127.0.0.1", 8888)

        mock_socket.close.assert_called_once()

    @patch("select.select")
    def test_create_client_sock_loop_on_einprogress(self, mock_select: MagicMock, mock_socket_class: MagicMock) -> None:
        mock_socket = mock_socket_class.return_value
        mock_socket.connect.side_effect = [OSError(errno.EINPROGRESS, "In progress."), None]

        mock_select.return_value = ([], [mock_socket], [])

        client_socket = create_client_sock("127.0.0.1", 1234)
        assert client_socket == mock_socket
        assert mock_socket.connect.call_count == 2

    @pytest.mark.parametrize("family_code, family_str", [
        (socket.AF_INET, "IPv4"),
        (socket.AF_INET6, "IPv6"),
        (socket.AF_UNIX, "Unix"),
        (67, "Unknown"),
    ])
    def test_get_socket_family_str(
        self, mock_sock: MagicMock, family_code: int, family_str: str
    ) -> None:
        mock_sock.family = family_code
        assert get_socket_family_str(mock_sock) == family_str

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_sock() -> MagicMock:
    return MagicMock(spec=socket.socket)

class TestSocketTransfer:
    MESSAGE: Final = b"hello world"
    MESSAGE_LEN: Final = len(MESSAGE)
    MESSAGE_HALF_LEN_A: Final = MESSAGE_LEN // 2
    MESSAGE_HALF_LEN_B: Final = MESSAGE_LEN - MESSAGE_HALF_LEN_A

    def test_socket_send_simple(self, mock_sock: MagicMock) -> None:
        mock_sock.send.return_value = self.MESSAGE_LEN
        socket_send(mock_sock, self.MESSAGE)
        mock_sock.send.assert_called_once_with(memoryview(self.MESSAGE))

    @patch("select.select")
    def test_socket_send_partial_and_retry(self, mock_select: MagicMock, mock_sock: MagicMock) -> None:
        mock_sock.send.side_effect = [
            self.MESSAGE_HALF_LEN_A,
            OSError(errno.EAGAIN, "Try again."),
            self.MESSAGE_HALF_LEN_B
        ]

        socket_send(mock_sock, self.MESSAGE)
        mock_select.assert_called_once_with([], [mock_sock], [])
        assert mock_sock.send.call_count == 3

    def test_socket_send_chunks(self, mock_sock: MagicMock) -> None:
        chunk_sizes = [2, 8, 1]
        assert sum(chunk_sizes) == self.MESSAGE_LEN

        mock_sock.send.side_effect = chunk_sizes
        socket_send(mock_sock, self.MESSAGE)
        assert mock_sock.send.call_count == 3

        calls = mock_sock.send.call_args_list

        assert calls[0] == call(memoryview(self.MESSAGE)[0:self.MESSAGE_LEN])
        assert calls[1] == call(memoryview(self.MESSAGE)[2:self.MESSAGE_LEN])
        assert calls[2] == call(memoryview(self.MESSAGE)[10:self.MESSAGE_LEN])

    def test_socket_send_timeout(self, mock_sock: MagicMock) -> None:
        mock_sock.send.side_effect = TimeoutError()

        with pytest.raises(SocketTimeoutError):
            socket_send(mock_sock, self.MESSAGE)

    def test_socket_send_disconnected(self, mock_sock: MagicMock) -> None:
        mock_sock.send.return_value = 0

        with pytest.raises(SocketDisconnectedError, match="Not enough data sent."):
            socket_send(mock_sock, self.MESSAGE)

    def test_socket_send_os_error_generic(self, mock_sock: MagicMock) -> None:
        mock_sock.send.side_effect = OSError(errno.ECONNRESET, "Connection reset.")

        with pytest.raises(SocketDisconnectedError, match="Unable to send data."):
            socket_send(mock_sock, self.MESSAGE)

    def test_socket_receive_simple(self, mock_sock: MagicMock) -> None:
        buffer = bytearray(self.MESSAGE_LEN)

        def mock_recv_into(buffer: memoryview, size: int) -> int:
            buffer[:size] = self.MESSAGE
            return size

        mock_sock.recv_into.side_effect = mock_recv_into
        socket_receive(mock_sock, buffer)

        assert buffer == self.MESSAGE
        mock_sock.recv_into.assert_called_once_with(memoryview(buffer), self.MESSAGE_LEN)

    @patch("select.select")
    def test_socket_receive_partial_and_retry(
        self, mock_select: MagicMock, mock_sock: MagicMock
    ) -> None:
        buffer = bytearray(self.MESSAGE_LEN)

        def mock_recv_into(buffer: memoryview, size: int) -> int:
            if mock_sock.recv_into.call_count == 1:
                assert size == self.MESSAGE_LEN
                buffer[:self.MESSAGE_HALF_LEN_A] = self.MESSAGE[:self.MESSAGE_HALF_LEN_A]
                return self.MESSAGE_HALF_LEN_A

            if mock_sock.recv_into.call_count == 2:
                raise OSError(errno.EAGAIN, "Try again.")

            buffer[:self.MESSAGE_HALF_LEN_B] = self.MESSAGE[self.MESSAGE_HALF_LEN_A:]
            return self.MESSAGE_HALF_LEN_B

        mock_sock.recv_into.side_effect = mock_recv_into
        socket_receive(mock_sock, buffer)

        assert buffer == self.MESSAGE
        mock_select.assert_called_once_with([mock_sock], [], [])
        assert mock_sock.recv_into.call_count == 3

    def test_socket_receive_timeout(self, mock_sock: MagicMock) -> None:
        buffer = bytearray(self.MESSAGE_LEN)
        mock_sock.recv_into.side_effect = TimeoutError()

        with pytest.raises(SocketTimeoutError):
            socket_receive(mock_sock, buffer)

    def test_socket_receive_disconnected(self, mock_sock: MagicMock) -> None:
        buffer = bytearray(self.MESSAGE_LEN)
        mock_sock.recv_into.return_value = 0

        with pytest.raises(SocketDisconnectedError, match="Not enough data received."):
            socket_receive(mock_sock, buffer)

    def test_socket_receive_os_error_generic(self, mock_sock: MagicMock) -> None:
        buffer = bytearray(self.MESSAGE_LEN)
        mock_sock.recv_into.side_effect = OSError(errno.ECONNRESET, "Connection reset.")

        with pytest.raises(SocketDisconnectedError, match="Unable to receive data."):
            socket_receive(mock_sock, buffer)

# ------------------------------------------------------------------------------

class TestSocketWrapper:
    def test_socket_context_manager(self) -> None:
        mock_sock = MagicMock()
        with Socket(mock_sock) as socket_wrap:
            assert socket_wrap.sock == mock_sock

        mock_sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        mock_sock.close.assert_called_once()

    def test_socket_context_manager_keep_open(self) -> None:
        mock_sock = MagicMock()
        with Socket(mock_sock, keep_open=True) as socket_wrap:
            assert socket_wrap.sock == mock_sock

        mock_sock.shutdown.assert_not_called()
        mock_sock.close.assert_not_called()
