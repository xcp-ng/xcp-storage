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
from xcp_storage.config.platform import get_exec_path
from xcp_storage.utils.process import run_command
from xcp_storage.utils.service import (
    is_service_active,
    restart_service,
    start_service,
    stop_service,
)

from xcp_storage.typing import Final, List, Optional, Tuple

# ==============================================================================

LINSTOR_CONTROLLER_PORT_PLAIN: Final = 3370
LINSTOR_CONTROLLER_PORT_SSL: Final = 3371

# URI of a controller (plain REST API): `linstor://<address>[:<port>]`.
LINSTOR_URI_PREFIX: Final = "linstor://"

# ------------------------------------------------------------------------------

_EXEC_PATH_SS: Final = get_exec_path("/usr/sbin/ss", {"debian": "/usr/bin/ss"})

_SERVICE_LINSTOR_CONTROLLER: Final = "linstor-controller"

# ------------------------------------------------------------------------------

class LinstorController:
    @staticmethod
    def get_addresses() -> List[str]:
        stdout = run_command([
            _EXEC_PATH_SS, "-tnH", "state", "established",
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
        return cls.format_uri(addresses[0]) if addresses else ""

    @staticmethod
    def format_uri(address: str, port: Optional[int] = None) -> str:
        """
        Format the URI of a controller at `address` (an IPv6 address is enclosed in brackets, if not already),
        on `port` (`None`: the default port).
        """

        if ":" in address and not address.startswith("["):
            address = f"[{address}]"
        uri = f"{LINSTOR_URI_PREFIX}{address}"
        return uri if port is None else f"{uri}:{port}"

    @staticmethod
    def parse_uri(uri: str) -> Tuple[str, Optional[int]]:
        """
        Return a parsed URI:
        - Address (an IPv4 or IPv6 address without its brackets).
        - Port (can be `None`: the default port) of the controller.
        """

        if not uri.startswith(LINSTOR_URI_PREFIX):
            raise ValueError(f"Not a LINSTOR URI: `{uri}`.")

        location = uri[len(LINSTOR_URI_PREFIX):]
        if location.startswith("["):
            # IPv6 address: `[<address>]` or `[<address>]:<port>`.
            address, bracket, port_suffix = location[1:].partition("]")
            if not bracket or (port_suffix and not port_suffix.startswith(":")):
                raise ValueError(f"Invalid address in LINSTOR URI: `{uri}`.")
            port_str = port_suffix[1:]
        else:
            address, _, port_str = location.partition(":")
        if not address:
            raise ValueError(f"Invalid address in LINSTOR URI: `{uri}`.")

        try:
            return address, int(port_str) if port_str else None
        except ValueError:
            raise ValueError(f"Invalid port in LINSTOR URI: `{uri}`.") from None

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
