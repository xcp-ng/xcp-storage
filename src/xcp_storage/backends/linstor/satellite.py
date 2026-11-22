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

from xcp_storage.utils.service import (
    disable_and_stop_service,
    enable_and_start_service,
    is_service_active,
)

from xcp_storage.typing import Final

# ==============================================================================

LINSTOR_SATELLITE_SERVICE: Final = "linstor-satellite"

LINSTOR_SATELLITE_PORT_PLAIN: Final = 3366
LINSTOR_SATELLITE_PORT_SSL: Final = 3367

# ------------------------------------------------------------------------------

class LinstorSatellite:
    @staticmethod
    def is_running() -> bool:
        return is_service_active(LINSTOR_SATELLITE_SERVICE)

    @staticmethod
    def enable_and_start() -> None:
        enable_and_start_service(LINSTOR_SATELLITE_SERVICE)

    @staticmethod
    def disable_and_stop() -> None:
        disable_and_stop_service(LINSTOR_SATELLITE_SERVICE)
