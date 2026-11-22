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

import threading
from unittest.mock import create_autospec, MagicMock, patch

import pytest

from xcp_storage.config.platform import POOL_BACKEND_TYPE, PoolBackendType
from xcp_storage.pool import _POOL_BACKEND_TYPE_TO_FACTORY, watch_pool_host_addresses
from xcp_storage.pool.interface import PoolBackend

from xcp_storage.typing import Dict, Final, Iterator, List

# ==============================================================================

_POOL_MODULE: Final = watch_pool_host_addresses.__module__

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_create_pool_backend() -> Iterator[MagicMock]:
    with patch(f"{_POOL_MODULE}._create_pool_backend", autospec=True) as mock_create_pool_backend:
        yield mock_create_pool_backend

@pytest.fixture
def mock_pool_backend(mock_create_pool_backend: MagicMock) -> MagicMock:
    mock_pool_backend = create_autospec(PoolBackend, instance=True)
    mock_create_pool_backend.return_value = mock_pool_backend
    return mock_pool_backend

# ------------------------------------------------------------------------------

class TestPoolBackend:
    def test_every_backend_type_has_factory(self) -> None:
        assert set(_POOL_BACKEND_TYPE_TO_FACTORY) == set(PoolBackendType)

    @pytest.mark.usefixtures("mock_pool_backend")
    def test_build_backend(self, mock_create_pool_backend: MagicMock) -> None:
        # Backend of the build configuration (CMake preset).
        watch_pool_host_addresses(lambda _addresses: None, threading.Event())
        mock_create_pool_backend.assert_called_once_with(POOL_BACKEND_TYPE)

    def test_watch_host_addresses(self, mock_pool_backend: MagicMock) -> None:
        changes: List[Dict[str, str]] = []
        stop_event = threading.Event()
        watch_pool_host_addresses(changes.append, stop_event)
        mock_pool_backend.watch_host_addresses.assert_called_once_with(changes.append, stop_event)
