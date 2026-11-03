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

from unittest.mock import DEFAULT, MagicMock, patch

import pytest

from xcp_storage.backends.linstor.controller import LinstorController
from xcp_storage.backends.linstor.satellite import LinstorSatellite

from xcp_storage.typing import (
    Dict,
    Iterator,
    NamedTuple,
    Tuple,
    Type,
    Union,
)

# ==============================================================================

class LinstorServiceSpec(NamedTuple):
    linstor_class: Union[Type[LinstorController], Type[LinstorSatellite]]
    service_name: str
    # Commands of the class: each one calls the function `<command>_service`.
    commands: Tuple[str, ...]

    @property
    def module_name(self) -> str:
        # Module patched by the mocks: the one that imports the service functions.
        return self.linstor_class.__module__

    @staticmethod
    def get_service_function_name(command: str) -> str:
        return f"{command}_service"

# ------------------------------------------------------------------------------

class LinstorServiceTests:
    """
    Tests of the service of a LINSTOR class, run by each subclass (`Test*`).

    A subclass provides the fixtures `linstor_service_spec` (`LinstorServiceSpec`) and
    `command` (parametrized on the commands of the service).
    """

    @pytest.fixture
    def mock_is_service_active(self, linstor_service_spec: LinstorServiceSpec) -> Iterator[MagicMock]:
        with patch(f"{linstor_service_spec.module_name}.is_service_active", autospec=True) as mock_is_service_active:
            yield mock_is_service_active

    @pytest.fixture
    def mock_service_functions(self, linstor_service_spec: LinstorServiceSpec) -> Iterator[Dict[str, MagicMock]]:
        function_names = map(linstor_service_spec.get_service_function_name, linstor_service_spec.commands)
        functions = dict.fromkeys(function_names, DEFAULT)
        with patch.multiple(linstor_service_spec.module_name, autospec=True, **functions) as mock_service_functions:
            yield mock_service_functions

    def test_running(self, linstor_service_spec: LinstorServiceSpec, mock_is_service_active: MagicMock) -> None:
        mock_is_service_active.return_value = True
        assert linstor_service_spec.linstor_class.is_running()
        mock_is_service_active.assert_called_once_with(linstor_service_spec.service_name)

    def test_not_running(self, linstor_service_spec: LinstorServiceSpec, mock_is_service_active: MagicMock) -> None:
        mock_is_service_active.return_value = False
        assert not linstor_service_spec.linstor_class.is_running()
        mock_is_service_active.assert_called_once_with(linstor_service_spec.service_name)

    def test_service_command(
        self,
        linstor_service_spec: LinstorServiceSpec,
        command: str,
        mock_service_functions: Dict[str, MagicMock]
    ) -> None:
        getattr(linstor_service_spec.linstor_class, command)()

        target_function_name = linstor_service_spec.get_service_function_name(command)
        for function_name, mock_service_function in mock_service_functions.items():
            if function_name == target_function_name:
                mock_service_function.assert_called_once_with(linstor_service_spec.service_name)
            else:
                mock_service_function.assert_not_called()
