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

from xcp_storage.rpc.server import RpcApiServer
from xcp_storage_cli.args import DEFAULT_INDENT, DEFAULT_TIMEOUT, GlobalArgs

# ==============================================================================

@pytest.fixture
def args_with_server(rpc_server: RpcApiServer) -> GlobalArgs:
    return GlobalArgs(
        rpc_server.address,
        rpc_server.port,
        DEFAULT_TIMEOUT,
        DEFAULT_INDENT,
        ca_native=False,
        ca_certificate=None,
        ca_directory=None
    )
