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

from tests.backends.drbd import (  # noqa: F401
    create_drbd_json_status,
    drbd_debug_fs,
    DrbdStatusNode,
    TEST_DRBD_PRIMARY_NODE_ADDRESS,
    TEST_DRBD_PRIMARY_NODE_NAME,
    TEST_DRBD_RESOURCE_NAME,
    TEST_DRBD_SECONDARY_NODE_ADDRESS,
    TEST_DRBD_SECONDARY_NODE_NAME,
)
from xcp_storage.backends.drbd import DrbdRole

from xcp_storage.typing import Final

# ==============================================================================

# Nodes of the DRBD statuses of the mocked tests (`drbd_json_status_*`).
_DRBD_PRIMARY_NODE: Final = DrbdStatusNode(
    1, TEST_DRBD_PRIMARY_NODE_NAME, TEST_DRBD_PRIMARY_NODE_ADDRESS, DrbdRole.PRIMARY
)
_DRBD_SECONDARY_NODE: Final = DrbdStatusNode(
    0, TEST_DRBD_SECONDARY_NODE_NAME, TEST_DRBD_SECONDARY_NODE_ADDRESS, DrbdRole.SECONDARY
)

# ------------------------------------------------------------------------------
# Statuses of `drbdsetup status --json` (`mock_run_command`), for the mocked tests.
# ------------------------------------------------------------------------------

@pytest.fixture
def drbd_json_status_primary() -> str:
    return create_drbd_json_status(TEST_DRBD_RESOURCE_NAME, _DRBD_PRIMARY_NODE, [_DRBD_SECONDARY_NODE])

@pytest.fixture
def drbd_json_status_secondary() -> str:
    return create_drbd_json_status(TEST_DRBD_RESOURCE_NAME, _DRBD_SECONDARY_NODE, [_DRBD_PRIMARY_NODE])

@pytest.fixture
def drbd_json_status_primary_two_volumes() -> str:
    return create_drbd_json_status(
        TEST_DRBD_RESOURCE_NAME, _DRBD_PRIMARY_NODE, [_DRBD_SECONDARY_NODE], volume_numbers=(0, 1)
    )
