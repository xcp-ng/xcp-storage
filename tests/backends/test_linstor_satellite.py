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

from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from xcp_storage.backends.linstor.satellite import _SERVICE_LINSTOR_SATELLITE, LinstorSatellite

from xcp_storage.typing import Final

# ==============================================================================

MODULE_NAME: Final = "xcp_storage.backends.linstor.satellite"

# ------------------------------------------------------------------------------

class TestLinstorSatelliteService:
    @patch(f"{MODULE_NAME}.is_service_active", return_value=True)
    def test_running(self, mock_is_service_active: MagicMock) -> None:
        assert LinstorSatellite.is_running()
        mock_is_service_active.assert_called_once_with(_SERVICE_LINSTOR_SATELLITE)

    @patch(f"{MODULE_NAME}.is_service_active", return_value=False)
    def test_not_running(self, mock_is_service_active: MagicMock) -> None:
        assert not LinstorSatellite.is_running()
        mock_is_service_active.assert_called_once_with(_SERVICE_LINSTOR_SATELLITE)

    @pytest.mark.parametrize("service_name, function_name", [
        ("enable_and_start", "enable_and_start_service"),
        ("disable_and_stop", "disable_and_stop_service")
    ])
    def test_service_command(self, service_name: str, function_name: str) -> None:
        with patch(f"{MODULE_NAME}.{function_name}") as mock_function_name:
            getattr(LinstorSatellite, service_name)()
        mock_function_name.assert_called_once_with(_SERVICE_LINSTOR_SATELLITE)
