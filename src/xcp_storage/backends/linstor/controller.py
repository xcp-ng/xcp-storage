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

from xcp_storage.backends.linstor.satellite import LINSTOR_SATELLITE_PORT_PLAIN, LINSTOR_SATELLITE_PORT_SSL
from xcp_storage.utils.process import run_command
from xcp_storage.utils.service import (
    is_service_active,
    restart_service,
    start_service,
    stop_service,
)

from xcp_storage.typing import Final, List

# ==============================================================================

LINSTOR_CONTROLLER_PORT_PLAIN: Final = 3370
LINSTOR_CONTROLLER_PORT_SSL: Final = 3371

# ------------------------------------------------------------------------------

_EXEC_PATH_SS: Final = "/usr/sbin/ss"

_SERVICE_LINSTOR_CONTROLLER: Final = "linstor-controller"

# ------------------------------------------------------------------------------

class LinstorController:
    @staticmethod
    def get_addresses() -> List[str]:
        stdout = run_command([
            _EXEC_PATH_SS, "-tnpH", "state", "established",
            f"( sport = :{LINSTOR_SATELLITE_PORT_PLAIN} or sport = :{LINSTOR_SATELLITE_PORT_SSL} )"
        ], expected_ret_code=0)
        return [
            line.split()[3].rsplit(":", 1)[0]
            for line in stdout.splitlines()
        ]

    @classmethod
    def get_uri(cls) -> str:
        # TODO(XCPNG-3033): On caller side, check that an IP address from the current pool is returned.
        addresses = cls.get_addresses()
        return "linstor://" + addresses[0] if addresses else ""

    @staticmethod
    def is_running() -> bool:
        return is_service_active(_SERVICE_LINSTOR_CONTROLLER)

    @staticmethod
    def start() -> None:
        start_service(_SERVICE_LINSTOR_CONTROLLER)

    @staticmethod
    def stop() -> None:
        stop_service(_SERVICE_LINSTOR_CONTROLLER)

    @staticmethod
    def restart() -> None:
        restart_service(_SERVICE_LINSTOR_CONTROLLER)
