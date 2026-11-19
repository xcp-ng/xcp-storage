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

import json

from tests import BUILD_CONFIG_CMAKE_VARIABLE_PREFIX, get_build_config_cmake_variables, PROJECT_PATH

from xcp_storage.typing import Final

# ==============================================================================

CMAKE_PRESETS_PATH: Final = PROJECT_PATH / "CMakePresets.json"

# ------------------------------------------------------------------------------

class TestBuildConfig:
    def test_cmake_variables_consistency(self) -> None:
        expected_names = set(get_build_config_cmake_variables())
        presets = json.loads(CMAKE_PRESETS_PATH.read_text(encoding="utf-8"))["configurePresets"]
        for preset in presets:
            names = {name for name in preset["cacheVariables"] if name.startswith(BUILD_CONFIG_CMAKE_VARIABLE_PREFIX)}
            assert names == expected_names, preset["name"]
