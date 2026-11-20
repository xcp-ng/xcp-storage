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

from xcp_storage.connectors.xapi.pool import watch_pool_host_addresses
from xcp_storage.pool.interface import PoolBackend

from xcp_storage.typing import Callable, Dict, override

# ==============================================================================

class XapiPoolBackend(PoolBackend):
    """
    Pool managed by XAPI.
    """

    @override
    def watch_host_addresses(
        self,
        on_change: Callable[[Dict[str, str]], None],
        stop_event: threading.Event
    ) -> None:
        watch_pool_host_addresses(on_change, stop_event)
