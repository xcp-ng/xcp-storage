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

from pathlib import Path
from unittest.mock import create_autospec, MagicMock, patch

import pytest

from tests.utils.exception import raises_exactly
from xcp_storage.utils.firewall import (
    _get_firewall_backend,
    create_firewall_allowlist,
    update_firewall_allowlist,
    update_firewall_tcp_port,
    update_firewall_tcp_port_range,
)
from xcp_storage.utils.firewall.interface import FirewallBackend, FirewallError
from xcp_storage.utils.firewall.iptables import IptablesFirewallBackend
from xcp_storage.utils.lock.file import FileLock

from xcp_storage.typing import Final, Iterator

# ==============================================================================

_FIREWALL_MODULE: Final = update_firewall_tcp_port.__module__

# ------------------------------------------------------------------------------

@pytest.fixture
def firewall_lock_path(tmp_path: Path) -> Iterator[Path]:
    # In a missing directory: created by the module.
    firewall_lock_path = tmp_path / "locks" / "firewall.lock"
    with patch(f"{_FIREWALL_MODULE}._LOCK_PATH", firewall_lock_path):
        yield firewall_lock_path

@pytest.fixture
def mock_firewall_backend(firewall_lock_path: Path) -> Iterator[MagicMock]:
    # Every method checks that it is called under the lock.
    mock_firewall_backend = create_autospec(FirewallBackend, instance=True)

    def check_locked(*_args: object, **_kwargs: object) -> None:
        assert not FileLock(firewall_lock_path).try_acquire()

    for method in (
        mock_firewall_backend.update_tcp_port,
        mock_firewall_backend.update_tcp_port_range,
        mock_firewall_backend.create_allowlist,
        mock_firewall_backend.update_allowlist,
    ):
        method.side_effect = check_locked
    with patch(f"{_FIREWALL_MODULE}._get_firewall_backend", autospec=True, return_value=mock_firewall_backend):
        yield mock_firewall_backend

# ------------------------------------------------------------------------------

class TestFirewall:
    ALLOWLIST: Final = "test-hosts"
    ADDRESSES: Final = ("10.30.43.1", "10.30.43.2")

    def test_backend(self) -> None:
        assert isinstance(_get_firewall_backend(), IptablesFirewallBackend)

    def test_update_tcp_port(self, mock_firewall_backend: MagicMock) -> None:
        update_firewall_tcp_port(80, open_port=True, allowlist=self.ALLOWLIST)
        mock_firewall_backend.update_tcp_port.assert_called_once_with(
            80, open_port=True, stateful=True, allowlist=self.ALLOWLIST
        )

    def test_update_tcp_port_range(self, mock_firewall_backend: MagicMock) -> None:
        update_firewall_tcp_port_range((80, 90), open_ports=False, stateful=False)
        mock_firewall_backend.update_tcp_port_range.assert_called_once_with(
            (80, 90), open_ports=False, stateful=False, allowlist=None
        )

    def test_create_allowlist(self, mock_firewall_backend: MagicMock) -> None:
        create_firewall_allowlist(self.ALLOWLIST)
        mock_firewall_backend.create_allowlist.assert_called_once_with(self.ALLOWLIST)

    def test_update_allowlist(self, mock_firewall_backend: MagicMock) -> None:
        update_firewall_allowlist(self.ALLOWLIST, self.ADDRESSES)
        mock_firewall_backend.update_allowlist.assert_called_once_with(self.ALLOWLIST, self.ADDRESSES)

    def test_lock_released_after_error(self, firewall_lock_path: Path, mock_firewall_backend: MagicMock) -> None:
        mock_firewall_backend.update_allowlist.side_effect = FirewallError("boom")
        with raises_exactly(FirewallError, "boom"):
            update_firewall_allowlist(self.ALLOWLIST, self.ADDRESSES)

        lock = FileLock(firewall_lock_path)
        assert lock.try_acquire()
        lock.release()
