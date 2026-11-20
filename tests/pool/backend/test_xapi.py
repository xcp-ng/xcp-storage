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
from unittest.mock import MagicMock, patch

import pytest

from xcp_storage.config.platform import PoolBackendType
from xcp_storage.pool import _create_pool_backend
from xcp_storage.pool.backend.xapi import XapiPoolBackend

from xcp_storage.typing import Dict, Final, Iterator, List

# ==============================================================================

_XAPI_POOL_BACKEND_MODULE: Final = XapiPoolBackend.__module__

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_watch_pool_host_addresses() -> Iterator[MagicMock]:
    with patch(
        f"{_XAPI_POOL_BACKEND_MODULE}.watch_pool_host_addresses", autospec=True
    ) as mock_watch_pool_host_addresses:
        yield mock_watch_pool_host_addresses

# ------------------------------------------------------------------------------

class TestXapiPoolBackend:
    def test_create_backend(self) -> None:
        assert type(_create_pool_backend(PoolBackendType.XAPI)) is XapiPoolBackend

    def test_watch_host_addresses(self, mock_watch_pool_host_addresses: MagicMock) -> None:
        changes: List[Dict[str, str]] = []
        stop_event = threading.Event()
        XapiPoolBackend().watch_host_addresses(changes.append, stop_event)
        mock_watch_pool_host_addresses.assert_called_once_with(changes.append, stop_event)
