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

import contextlib
import errno
import ipaddress
import select
import socket
import ssl
from types import TracebackType

from xcp_storage.typing import (
    Any,
    Dict,
    Final,
    Iterator,
    Optional,
    override,
    Tuple,
    Type,
    Union,
)

# ==============================================================================

_FAMILY_TO_STR: Final = {
    socket.AF_INET: "IPv4",
    socket.AF_INET6: "IPv6",
    socket.AF_UNIX: "Unix"
}

_IP_VERSION_TO_FAMILY: Final = {
    4: socket.AF_INET,
    6: socket.AF_INET6,
    0: socket.AF_UNSPEC
}

_SERVER_BACKLOG: Final = 128

_MAX_PORT: Final = 65535

# Default buffer size used for receiving socket data.
# Large enough to avoid impacting performance while remaining compatible with most platforms.
_RECEIVE_BUFFER_SIZE: Final = 8192

# ------------------------------------------------------------------------------

class SocketError(Exception):
    """
    Base class of the errors of this module: its helpers only raise errors derived from it.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

class SocketTimeoutError(SocketError):
    """
    An operation (connection, send, receive, ...) did not complete in time.
    """

    def __init__(self) -> None:
        super().__init__("Socket timeout.")

class SocketNotListeningError(SocketError):
    """
    Nobody listens on the address. Only raised UNIX clients: no socket file, or a stale one.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

class SocketBusyError(SocketError):
    """
    The peer cannot accept new connections for now (its listen queue is full):
    trying again later can succeed. Only raised by UNIX clients.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

class SocketDisconnectedError(SocketError):
    """
    The connection is closed or lost: the socket is closed, the peer closed it or reset it,
    or a transfer ended before all the data was sent or received.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

class SocketCertificateError(SocketError):
    """
    The certificate of a server cannot be verified (untrusted, hostname mismatch...).
    Trying again does not help.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

# ------------------------------------------------------------------------------

def get_ip_address(address: str, ip_version: int = 0) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    """
    Resolve `address` to an IP address.

    `address` can be a literal IP or a hostname, resolved via `socket.getaddrinfo()`.
    For a hostname, the first address returned by the system is used.
    If `address` is empty, the local hostname is resolved.

    `ip_version` can be set to 0 to accept any version, 4 or 6 to require a specific one.
    """

    family = _IP_VERSION_TO_FAMILY.get(ip_version)
    if family is None:
        raise SocketError("Unknown IP version.")

    # Note: `address` can be a hostname or IP.
    ip_address: Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = None
    with contextlib.suppress(ValueError):
        ip_address = ipaddress.ip_address(address)

    if ip_address is not None:
        if family is not socket.AF_UNSPEC and ip_address.version != ip_version:
            raise SocketError(
                f"IP version mismatch for `{address}`: "
                f"got IPv{ip_address.version} address, expected IPv{ip_version}."
            )
        return ip_address

    try:
        info = socket.getaddrinfo(
            address or socket.gethostname(), 80, family, socket.SOCK_STREAM, socket.IPPROTO_TCP, socket.AI_ADDRCONFIG
        )
        return ipaddress.ip_address(info[0][4][0])
    except socket.gaierror as e:
        raise SocketError("Cannot resolve IP.") from e
    except IndexError:
        raise SocketError("Cannot resolve IP: no valid address.") from None
    except ValueError:
        raise SocketError("Cannot resolve IP: malformed address.") from None

# ------------------------------------------------------------------------------

IPv4SocketAddress = Tuple[str, int]
IPv6SocketAddress = Tuple[str, int, int, int]
SocketAddress = Union[IPv4SocketAddress, IPv6SocketAddress]

def format_address(address: str, port: int) -> Tuple[socket.AddressFamily, SocketAddress]:
    if not address:
        raise SocketError("No hostname/IP.")
    if not 0 <= port <= _MAX_PORT:
        raise SocketError(f"Port out of range: {port}.")

    ip_address = get_ip_address(address)
    if ip_address.version == 4:
        family = socket.AF_INET
        return (family, (str(ip_address), port))
    if ip_address.version == 6:
        family = socket.AF_INET6
        return (family, (str(ip_address), port, 0, 0))

    raise SocketError("Unknown IP version.")

# ------------------------------------------------------------------------------

def _create_stream_sock(family: int) -> socket.socket:
    try:
        return socket.socket(family, socket.SOCK_STREAM)
    except OSError as e:
        raise SocketError("Failed to create sock.") from e

def _create_tcp_sock(
    address: str,
    family: socket.AddressFamily,
    *,
    bind: bool,
    reuse_address: bool,
    ssl_context: Optional[ssl.SSLContext]
) -> socket.socket:
    sock = _create_stream_sock(family)
    with _close_sock_on_error(sock):
        if ssl_context:
            try:
                if bind:
                    sock = ssl_context.wrap_socket(sock, server_side=True)
                else:
                    sock = ssl_context.wrap_socket(sock, server_side=False, server_hostname=address or None)
            except (OSError, ValueError) as e:
                raise SocketError("Failed to wrap sock with TLS.") from e

    if reuse_address:
        set_socket_reuseaddr(sock)

    return sock

# ------------------------------------------------------------------------------

def _normalize_timeout(timeout: Optional[float]) -> Optional[float]:
    # The sockets created by this module are blocking (with or without timeout), so `0` must be
    # normalized away: `settimeout(0)` would put the socket in non-blocking mode, where `connect()`
    # raises `EINPROGRESS` and no completion path exists here.
    # Note: `socket_send`/`socket_receive` support non-blocking sockets given by the caller.
    if timeout is not None and timeout <= 0:
        timeout = None
    return timeout

def _normalize_and_set_sock_timeout(sock: socket.socket, timeout: Optional[float]) -> None:
    timeout = _normalize_timeout(timeout)
    try:
        # Always called, including with `None`, so that blocking mode can be restored.
        sock.settimeout(timeout)
    except OSError as e:
        raise SocketError("Failed to set sock timeout.") from e
    except (ValueError, OverflowError) as e:
        # `nan` is refused with `ValueError`, a too big value with `OverflowError`.
        raise SocketError("Invalid sock timeout.") from e

@contextlib.contextmanager
def _raise_on_sock_timeout() -> Iterator[None]:
    try:
        yield
    # TODO(XCPNG-3032): `socket.timeout` is a workaround for python 3.6. Must be removed later.
    except (TimeoutError, socket.timeout):
        raise SocketTimeoutError() from None

# ------------------------------------------------------------------------------

@contextlib.contextmanager
def _close_sock_on_error(*socks: socket.socket) -> Iterator[None]:
    try:
        yield
    except BaseException:
        for sock in socks:
            with contextlib.suppress(Exception):
                sock.close()
        raise

# ------------------------------------------------------------------------------

def _is_certificate_error(exception: Exception) -> bool:
    # TODO(XCPNG-3032): Workaround for old python versions. Remove me later.
    # We can't use `ssl.SSLCertVerificationError`: it only exists since Python 3.7.
    # So we use:
    # - `ssl.CertificateError` for a hostname mismatch.
    # - `ssl.SSLError` with the reason to check failed cert verification.
    return (
        isinstance(exception, ssl.CertificateError)
        or getattr(exception, "reason", None) == "CERTIFICATE_VERIFY_FAILED"
    )

# ------------------------------------------------------------------------------

def create_tcp_server_sock(
    address: str,
    port: int,
    *,
    reuse_address: bool = True,
    keep_alive: bool = True,
    timeout: Optional[float] = None,
    ssl_context: Optional[ssl.SSLContext] = None
) -> socket.socket:
    family, bind = format_address(address, port)
    sock = _create_tcp_sock(address, family, bind=True, reuse_address=reuse_address, ssl_context=ssl_context)
    with _close_sock_on_error(sock):
        _normalize_and_set_sock_timeout(sock, timeout)
        try:
            sock.bind(bind)
            sock.listen(_SERVER_BACKLOG)
        except OSError as e:
            raise SocketError("Failed to bind server sock.") from e

    if keep_alive:
        set_socket_keepalive(sock)

    return sock

def create_tcp_client_sock(
    address: str,
    port: int,
    *,
    reuse_address: bool = True,
    keep_alive: bool = True,
    timeout: Optional[float] = None,
    ssl_context: Optional[ssl.SSLContext] = None,
    source_address: Optional[str] = None,
    source_port: int = 0
) -> socket.socket:
    family, connect = format_address(address, port)
    sock = _create_tcp_sock(address, family, bind=False, reuse_address=reuse_address, ssl_context=ssl_context)
    with _close_sock_on_error(sock):
        _normalize_and_set_sock_timeout(sock, timeout)
        try:
            if source_address:
                _, bind = format_address(source_address, source_port)
                sock.bind(bind)
            with _raise_on_sock_timeout():
                sock.connect(connect)
        except (OSError, ssl.CertificateError) as e:
            if _is_certificate_error(e):
                raise SocketCertificateError("Failed to verify the server certificate.") from e
            raise SocketError("Failed to connect client sock.") from e

    if keep_alive:
        set_socket_keepalive(sock)

    return sock

# ------------------------------------------------------------------------------

def create_unix_server_sock(path: str, *, timeout: Optional[float] = None) -> socket.socket:
    sock = _create_stream_sock(socket.AF_UNIX)
    with _close_sock_on_error(sock):
        _normalize_and_set_sock_timeout(sock, timeout)
        try:
            sock.bind(path)
            sock.listen(_SERVER_BACKLOG)
        except OSError as e:
            raise SocketError("Failed to bind UNIX server sock.") from e

    return sock

def create_unix_client_sock(path: str, *, timeout: Optional[float] = None) -> socket.socket:
    sock = _create_stream_sock(socket.AF_UNIX)
    with _close_sock_on_error(sock):
        _normalize_and_set_sock_timeout(sock, timeout)
        try:
            with _raise_on_sock_timeout():
                sock.connect(path)
        except OSError as e:
            if e.errno in (errno.ENOENT, errno.ECONNREFUSED):
                raise SocketNotListeningError("Nobody listens on UNIX sock.") from e
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                raise SocketBusyError("UNIX server sock is busy.") from e
            raise SocketError("Failed to connect UNIX client sock.") from e

    return sock

# ------------------------------------------------------------------------------

SocketPair = Tuple[socket.socket, socket.socket]

def create_socket_pair(*, timeout: Optional[float] = None) -> SocketPair:
    try:
        first, second = socket.socketpair()
    except OSError as e:
        raise SocketError("Failed to create sock pair.") from e

    with _close_sock_on_error(first, second):
        _normalize_and_set_sock_timeout(first, timeout)
        _normalize_and_set_sock_timeout(second, timeout)

    return first, second

# ------------------------------------------------------------------------------

def set_socket_reuseaddr(sock: socket.socket) -> None:
    """
    Enable SO_REUSEADDR on `sock`.
    This allows the port to be re-bound while the previous connection is
    still in TIME_WAIT. Best-effort: any error is silently ignored.
    """

    with contextlib.suppress(Exception):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

def set_socket_keepalive(sock: socket.socket) -> None:
    """
    Enable SO_KEEPALIVE on `sock`.
    This turns on OS keep-alive probes so a silently-dead peer is eventually
    detected. Best-effort: any error is silently ignored.
    """

    with contextlib.suppress(Exception):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

# ------------------------------------------------------------------------------

def _get_buffer_size(buffer: Union[bytes, bytearray], size: Optional[int] = None) -> int:
    if size is None:
        return len(buffer)
    if size < 0 or size > len(buffer):
        raise SocketError(f"Size {size} is out of range for a buffer of length {len(buffer)}.")
    return size

# ------------------------------------------------------------------------------

def _wait_after_would_block(sock: socket.socket, *, writable: bool) -> None:
    action = "send" if writable else "receive"
    error_message = f"Unable to {action} data."
    try:
        if writable:
            select.select([], [sock], [])
        else:
            select.select([sock], [], [])
    except OSError as e:
        raise SocketDisconnectedError(error_message) from e
    except ValueError as e:
        if sock.fileno() < 0:
            raise SocketDisconnectedError(error_message) from e
        raise SocketError(f"Unable to {action} data: invalid argument.") from e

# ------------------------------------------------------------------------------

def socket_send(sock: socket.socket, buffer: bytes, size: Optional[int] = None) -> None:
    size = _get_buffer_size(buffer, size)
    view = memoryview(buffer)

    pos = 0
    while pos < size:
        try:
            with _raise_on_sock_timeout():
                n = sock.send(view[pos:size])
            if not n:
                break
            pos += n
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                _wait_after_would_block(sock, writable=True)
                continue
            raise SocketDisconnectedError("Unable to send data.") from e

    if pos != size:
        raise SocketDisconnectedError("Not enough data sent.") from None

# ------------------------------------------------------------------------------

def socket_receive(sock: socket.socket, buffer: bytearray, size: Optional[int] = None) -> None:
    size = _get_buffer_size(buffer, size)
    view = memoryview(buffer)

    pos = 0
    while pos < size:
        try:
            with _raise_on_sock_timeout():
                n = sock.recv_into(view[pos:], min(size - pos, _RECEIVE_BUFFER_SIZE))
            if not n:
                break
            pos += n
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                _wait_after_would_block(sock, writable=False)
                continue
            raise SocketDisconnectedError("Unable to receive data.") from e

    if pos != size:
        raise SocketDisconnectedError("Not enough data received.") from None

# ------------------------------------------------------------------------------

def socket_wait_readable(sock: socket.socket, *, timeout: Optional[float] = None) -> bool:
    if sock.fileno() < 0:
        raise SocketDisconnectedError("Unable to wait for data. Socket is closed.")

    # An SSL socket may already hold decrypted data that `select` cannot see.
    if isinstance(sock, ssl.SSLSocket) and sock.pending():
        return True

    try:
        readable, _, _ = select.select([sock], [], [], timeout)
    except OSError as e:
        raise SocketDisconnectedError("Unable to wait for data.") from e
    except (ValueError, OverflowError) as e:
        # Negative or too big timeout, or file descriptor out of range for `select`.
        raise SocketError("Unable to wait for data: invalid argument.") from e
    return bool(readable)

# ------------------------------------------------------------------------------

def get_socket_family_str(sock: socket.socket) -> str:
    return _FAMILY_TO_STR.get(sock.family, "Unknown")

def get_socket_address(sock: socket.socket) -> Optional[str]:
    try:
        name = sock.getsockname()
    except OSError:
        return None

    if sock.family == socket.AF_UNIX:
        # The name is the path, empty for an unnamed socket (e.g. client side or socket pair) and
        # `bytes` is returned for an abstract socket.
        return name if isinstance(name, str) and name else None
    return name[0]

def get_socket_port(sock: socket.socket) -> Optional[int]:
    if sock.family == socket.AF_UNIX:
        return None

    try:
        return sock.getsockname()[1]
    except OSError:
        return None

# ------------------------------------------------------------------------------

class Socket(contextlib.AbstractContextManager):
    def __init__(self, sock: socket.socket, *, keep_open: bool = False) -> None:
        self.sock = sock
        self.keep_open = keep_open

    def __del__(self) -> None:
        self.close()

    @override
    def __enter__(self) -> "Socket":
        # `Socket` is a socket manager/wrapper that does not create sockets directly.
        # It's simply built around a `socket.socket` instance; this is why `__enter__` does nothing,
        # whereas `__exit__` can close a connection.
        return self

    @override
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        self.close()

    def send(self, buffer: bytes, size: Optional[int] = None) -> None:
        socket_send(self.sock, buffer, size)

    def receive(self, buffer: bytearray, size: Optional[int] = None) -> None:
        socket_receive(self.sock, buffer, size)

    def wait_readable(self, *, timeout: Optional[float] = None) -> bool:
        return socket_wait_readable(self.sock, timeout=timeout)

    def close(self) -> None:
        if self.keep_open:
            return
        with contextlib.suppress(Exception):
            self.sock.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(Exception):
            self.sock.close()

    @property
    def family_str(self) -> str:
        return get_socket_family_str(self.sock)

    @property
    def address(self) -> Optional[str]:
        return get_socket_address(self.sock)

    @property
    def port(self) -> Optional[int]:
        return get_socket_port(self.sock)

    @property
    def timeout(self) -> Optional[float]:
        return self.sock.gettimeout()

    @timeout.setter
    def timeout(self, value: Optional[float]) -> None:
        _normalize_and_set_sock_timeout(self.sock, value)

    @property
    def peer_certificate(self) -> Optional[Dict[str, Any]]:
        if isinstance(self.sock, ssl.SSLSocket) and self.sock.fileno() >= 0:
            try:
                return self.sock.getpeercert()
            except (OSError, ValueError) as e:
                # `OSError`: not connected. `ValueError`: the handshake is not done yet.
                raise SocketError("Unable to get the peer certificate.") from e
        return None
