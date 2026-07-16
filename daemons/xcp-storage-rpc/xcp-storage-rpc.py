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

import configparser

from xcp_storage.rpc.server import RpcApiServer

from xcp_storage.typing import Final

# ==============================================================================

DEFAULT_ADDRESS: Final = "0.0.0.0" # noqa: S104
DEFAULT_PORT: Final = 3630

CONFIG_PATH: Final = "/etc/xcp-storage/rpc.conf"

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)

    address = config.get("network", "address", fallback=DEFAULT_ADDRESS)
    port = config.getint("network", "port", fallback=DEFAULT_PORT)

    # TODO(XCPNG-3037): Use SSL context.
    api_server = RpcApiServer(address, port, ssl_context=None)
    api_server.run()
