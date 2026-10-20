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

import pytest

from tests.network.tls import (  # noqa: F401
    client_ssl_context,
    ssl_contexts,
    tls_contexts,
)
from xcp_storage.network.socket import create_socket_pair, SocketPair

from xcp_storage.typing import Final, Generator

# ==============================================================================

SOCKET_PAIR_TIMEOUT: Final = 3.0

@pytest.fixture
def socket_pair() -> Generator[SocketPair, None, None]:
    first, second = create_socket_pair(timeout=SOCKET_PAIR_TIMEOUT)
    with first, second:
        yield first, second
