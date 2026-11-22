#!/usr/bin/env python3
#
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

import signal
import sys
import threading
from types import FrameType

import xcp_storage.log as log
from xcp_storage.pool import update_pool_host_addresses, watch_pool_host_addresses
from xcp_storage.version import XcpStorageVersion

from xcp_storage.typing import Dict, Optional

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

def publish_addresses(addresses: Dict[str, str]) -> None:
    logger.info(
        "Addresses of the pool hosts: %s.",
        ", ".join(f"{host_uuid}={address}" for host_uuid, address in sorted(addresses.items()))
    )
    update_pool_host_addresses(list(addresses.values()))

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(
        "Starting xcp-storage-pool-hosts %s with python %s.",
        XcpStorageVersion.get_description(),
        sys.version.split()[0]
    )

    stop_event = threading.Event()

    def handle_sigterm(_signal_number: int, _frame: Optional[FrameType]) -> None:
        logger.info("SIGTERM received, stopping...")
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_sigterm)
    watch_pool_host_addresses(publish_addresses, stop_event)
