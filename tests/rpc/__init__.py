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

from xcp_storage.rpc.client import RpcApiClient
from xcp_storage.utils.json.rpc import JsonRpcResponseServerError

from xcp_storage.typing import Callable, Final

# ==============================================================================

RPC_CLIENT_TIMEOUT: Final = 1.0

RpcClientFactory = Callable[..., RpcApiClient]

# ------------------------------------------------------------------------------

def assert_rpc_server_error_message(
    exc_info: "pytest.ExceptionInfo[JsonRpcResponseServerError]", message: str
) -> None:
    # The reason of a server error is in the data of the response.
    assert isinstance(exc_info.value.data, dict)
    assert message in str(exc_info.value.data["message"])
