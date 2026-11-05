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

from tests.backends.linstor import LinstorServiceSpec, LinstorServiceTests
from xcp_storage.backends.linstor.satellite import _SERVICE_LINSTOR_SATELLITE, LinstorSatellite

from xcp_storage.typing import Final

# ==============================================================================

_LINSTOR_SATELLITE_SERVICE_SPEC: Final = LinstorServiceSpec(
    LinstorSatellite,
    _SERVICE_LINSTOR_SATELLITE,
    ("enable_and_start", "disable_and_stop")
)

# ------------------------------------------------------------------------------

class TestLinstorSatelliteService(LinstorServiceTests):
    @pytest.fixture
    def linstor_service_spec(self) -> LinstorServiceSpec:
        return _LINSTOR_SATELLITE_SERVICE_SPEC

    @pytest.fixture(params=_LINSTOR_SATELLITE_SERVICE_SPEC.commands)
    def command(self, request: pytest.FixtureRequest) -> str:
        return request.param
