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

from tests.backends.drbd import DrbdDebugFs
from tests.network.tls import over_plain_and_tls
from tests.rpc import assert_rpc_server_error_message, RpcClientFactory
from tests.utils.process import ProcFs
import xcp_storage.rpc.api as api
from xcp_storage.utils.json.rpc import JsonRpcResponseServerError

from xcp_storage.typing import Final

# ==============================================================================

@over_plain_and_tls
class TestRpcModuleDrbd:
    RESOURCE_NAME: Final = "xcp-volume-rpc"

    def test_get_openers(
        self, drbd_debug_fs: DrbdDebugFs, proc_fs: ProcFs, rpc_client_factory: RpcClientFactory
    ) -> None:
        resource_name = self.RESOURCE_NAME
        volume_number = 1
        pid = 482584
        open_duration = 86143

        drbd_debug_fs.write_openers(resource_name, 0, f"other {pid + 1} {open_duration}\n")
        drbd_debug_fs.write_openers(resource_name, volume_number, f"tapback {pid} {open_duration}\n")
        proc_fs.write_cmdline(pid, b"tapback\x00-d\x00")

        rpc_client = rpc_client_factory()
        response = rpc_client.call_api(api.drbd.get_openers, resource_name=resource_name, volume_number=volume_number)

        assert response == [{
            "pid": pid,
            "process_name": "tapback",
            "cmdline": ["tapback", "-d"],
            "open_duration": open_duration,
            "auto_promoter": False
        }]

    @pytest.mark.usefixtures("drbd_debug_fs")
    def test_get_openers_with_invalid_resource_name(self, rpc_client_factory: RpcClientFactory) -> None:
        rpc_client = rpc_client_factory()
        with pytest.raises(JsonRpcResponseServerError) as exc_info:
            rpc_client.call_api(api.drbd.get_openers, resource_name="../../../tmp/x", volume_number=0)
        assert_rpc_server_error_message(exc_info, "Invalid DRBD resource name")

    @pytest.mark.usefixtures("drbd_debug_fs")
    def test_get_openers_with_invalid_volume_number(self, rpc_client_factory: RpcClientFactory) -> None:
        rpc_client = rpc_client_factory()
        with pytest.raises(JsonRpcResponseServerError) as exc_info:
            rpc_client.call_api(api.drbd.get_openers, self.RESOURCE_NAME, "0/../../x") # type: ignore[arg-type]
        assert_rpc_server_error_message(exc_info, "Not a DRBD volume number")
