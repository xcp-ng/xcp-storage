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

import xapi.storage.api.v5.plugin

from xcp_storage.connectors.smapi_v3.utils import (
    execute_plugin_command,
    handle_plugin_exception,
)
from xcp_storage.utils.decorator import decorate_all_methods
from xcp_storage.utils.json.rpc import JsonValue

from xcp_storage.typing import override

# ==============================================================================

@decorate_all_methods(handle_plugin_exception)
class Implementation(xapi.storage.api.v5.plugin.Plugin_skeleton):
    @override
    def query(self, dbg: str) -> JsonValue:
        return {
            "plugin": "tapdisk",
            "name": "Tapdisk datapath plugin.",
            "description": (
                "This plugin manages and configures tapdisk "
                "instances backend for RAW and Qcow2 images."
            ),
            "vendor": "Vates",
            "copyright": "(C) 2026 Vates SAS",
            "version": "3.0",
            "required_api_version": "5.0",
            "features": [
                "NONPERSISTENT",
                "VDI_MIRROR_IN",
                "VDI_MIRROR/2",
                "VDI_NONPERSISTENT"
            ],
            "configuration": {},
            "required_cluster_stack": []
        }

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    execute_plugin_command(xapi.storage.api.v5.plugin.Plugin_commandline(Implementation()))
