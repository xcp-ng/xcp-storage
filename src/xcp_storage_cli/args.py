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

import argparse
from dataclasses import dataclass
from pathlib import Path
import ssl
import sys

from xcp_storage.rpc.client import RpcApiClient

from xcp_storage.typing import Final, Optional

# ==============================================================================

DEFAULT_ADDRESS: Final = "127.0.0.1"
DEFAULT_PORT: Final = 3630
DEFAULT_TIMEOUT: Final = 3.0
DEFAULT_INDENT: Final = 4

# ------------------------------------------------------------------------------

def positive_int(arg: str) -> int:
    try:
        parsed_arg = int(arg)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Unable to parse an int number: {e}") from e

    if parsed_arg < 0:
        raise argparse.ArgumentTypeError(f"{arg} is a negative int, but a positive int was expected")

    return parsed_arg

def positive_float(arg: str) -> float:
    try:
        parsed_arg = float(arg)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Unable to parse a float number: {e}") from e

    if parsed_arg < 0:
        raise argparse.ArgumentTypeError(f"{arg} is a negative float, but a positive float was expected")

    return parsed_arg

def str_or_stdin(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()

    return arg

# ------------------------------------------------------------------------------

@dataclass
class GlobalArgs:
    address: str
    port: int
    timeout: float

    indent: int

    ca_native: bool
    ca_certificate: Optional[Path]
    ca_directory: Optional[Path]

    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        if not self.ca_native and not self.ca_certificate and not self.ca_directory:
            return None

        ssl_context = ssl.create_default_context(cafile=self.ca_certificate, capath=self.ca_directory)

        if self.ca_native:
            ssl_context.load_default_certs()

        return ssl_context

    def create_rpc_client(self) -> RpcApiClient:
        return RpcApiClient(self.address, self.port, self.create_ssl_context(), self.timeout)
