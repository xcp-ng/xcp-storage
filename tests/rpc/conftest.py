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

import threading
from typing import Generator

import pytest

from xcp_storage.rpc.server import RpcApiServer

# ==============================================================================

@pytest.fixture
def rpc_server() -> Generator[RpcApiServer, None, None]:
    server = RpcApiServer("127.0.0.1", 0)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    server.wait_for_startup()

    yield server

    server.stop()
    server_thread.join(timeout=2.0)
