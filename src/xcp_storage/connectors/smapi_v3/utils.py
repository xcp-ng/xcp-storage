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
import sys

import xapi
import xapi.storage.api.v5.datapath
import xapi.storage.api.v5.plugin
import xapi.storage.api.v5.volume
import xapi.storage.log as xapi_log

from xcp_storage.utils.exception import stringify_exception

from xcp_storage.typing import (
    Callable,
    ParamSpec,
    TypeVar,
    Union,
)

P = ParamSpec("P")
T = TypeVar("T")

# ==============================================================================

XapiPlugin = Union[
    xapi.storage.api.v5.datapath.Data_commandline,
    xapi.storage.api.v5.datapath.Datapath_commandline,
    xapi.storage.api.v5.plugin.Plugin_commandline,
    xapi.storage.api.v5.volume.SR_commandline,
    xapi.storage.api.v5.volume.Volume_commandline
]

# ------------------------------------------------------------------------------

def execute_plugin_command(command_line: XapiPlugin) -> None:
    xapi_log.log_call_argv()
    command_name = Path(sys.argv[0]).name
    method_name = command_name.split(".")[-1].lower()
    # Check on plugin implementation if we have the method name.
    if not method_name.startswith("_") and hasattr(command_line.impl, method_name):
        # Call method on command line helper (not the plugin implementation).
        method = getattr(command_line, method_name, None)
        if method:
            method()
            return
    else:
        raise xapi.Unimplemented(command_name)

def handle_plugin_exception(function: Callable[P, T]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            try:
                return function(*args, **kwargs)
            except xapi.Rpc_light_failure:
                raise
            except Exception as e:
                # TODO(XCPNG-3548): Map exceptions to xapi.Rpc_light_failure exception.
                xapi_log.error("Unhandled exception in XAPI storage plugin.", exc_info=True)
                raise xapi.InternalError(str(e)) from e
        except xapi.Rpc_light_failure as e:
            xapi_log.info("Reporting XAPI storage plugin failure `%s` to caller.", stringify_exception(e))
            raise
    return wrapper
