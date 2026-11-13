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
import socket

from xcp_storage.network.socket import (
    create_unix_client_sock,
    create_unix_server_sock,
    get_socket_port,
)

from xcp_storage.typing import (
    cast,
    Iterator,
    StrPath,
)

# ==============================================================================

def find_free_tcp_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return cast(int, get_socket_port(sock))

@contextlib.contextmanager
def busy_unix_server_sock(path: StrPath) -> Iterator[socket.socket]:
    """
    UNIX server sock listening on `path` that never accepts, its listen queue full: a new connection with a timeout
    fails at once with `SocketBusyError`.
    """

    with create_unix_server_sock(path) as unix_server:
        unix_server.listen(0)
        with create_unix_client_sock(path):
            yield unix_server
