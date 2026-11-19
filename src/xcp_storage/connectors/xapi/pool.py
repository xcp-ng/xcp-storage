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

import contextlib
import threading

import XenAPI

import xcp_storage.log as log

from xcp_storage.typing import (
    Any,
    Callable,
    Dict,
    Final,
    Optional,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

XapiSession = Any

# Origin of the sessions, shown by XAPI.
_XAPI_SESSION_ORIGINATOR: Final = "xcp-storage-pool-hosts"

# Class of the objects watched.
_XAPI_HOST_CLASS: Final = "host"

_XAPI_EVENT_FROM_TIMEOUT: Final = 30.0
_XAPI_SESSION_RETRY_DELAY: Final = 5.0

# ------------------------------------------------------------------------------

def _create_xapi_session() -> XapiSession:
    session = XenAPI.xapi_local()
    session.xenapi.login_with_password("root", "", "", _XAPI_SESSION_ORIGINATOR)
    return session

def _watch_pool_host_addresses(on_change: Callable[[Dict[str, str]], None], stop_event: threading.Event) -> None:
    session = _create_xapi_session()
    try:
        addresses: Optional[Dict[str, str]] = None
        token = ""
        while not stop_event.is_set():
            result = session.xenapi.event_from([_XAPI_HOST_CLASS], token, _XAPI_EVENT_FROM_TIMEOUT)
            token = result["token"]
            if not result["events"]:
                continue

            new_addresses = get_pool_host_addresses(session)
            if new_addresses != addresses:
                on_change(new_addresses)
                addresses = new_addresses
    finally:
        with contextlib.suppress(Exception):
            session.xenapi.session.logout()

# ------------------------------------------------------------------------------

def get_pool_host_addresses(session: XapiSession) -> Dict[str, str]:
    """
    Return the address of each host of the pool (`host.address`), by host UUID.
    """

    return {record["uuid"]: record["address"] for record in session.xenapi.host.get_all_records().values()}

def watch_pool_host_addresses(on_change: Callable[[Dict[str, str]], None], stop_event: threading.Event) -> None:
    """
    Call `on_change` with the addresses of the pool hosts, then each time they change,
    until `stop_event` is set.
    """

    while not stop_event.is_set():
        try:
            _watch_pool_host_addresses(on_change, stop_event)
        except Exception as e: # noqa: PERF203
            logger.warning(
                "Failed to watch or publish the addresses of the pool hosts, retried in %s s: `%s`.",
                _XAPI_SESSION_RETRY_DELAY,
                e
            )
            stop_event.wait(_XAPI_SESSION_RETRY_DELAY)
