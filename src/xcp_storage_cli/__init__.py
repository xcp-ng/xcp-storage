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
from pathlib import Path
import sys

import xcp_storage.log as log
from xcp_storage_cli.args import (
    DEFAULT_ADDRESS,
    DEFAULT_INDENT,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    GlobalArgs,
    positive_float,
    positive_int,
)
from xcp_storage_cli.commands import register_all_commands
from xcp_storage_cli.commands.command import Command

from xcp_storage.typing import Iterable, Optional, Tuple

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

def parse_args(args: Optional[Iterable[str]] = None) -> Tuple[Command, GlobalArgs]:
    parser = argparse.ArgumentParser(
        prog="xcp-storage-cli",
        description="CLI to interact with a xcp-storage RPC server.",
    )

    parser.add_argument(
        "--address",
        "-a",
        help="Address of the server.",
        default=DEFAULT_ADDRESS
    )

    parser.add_argument(
        "--port",
        "-p",
        help="Port of the server.",
        type=positive_int,
        default=DEFAULT_PORT
    )

    parser.add_argument(
        "--timeout",
        "-t",
        help="Maximum time in seconds to wait for a response from the server.",
        type=positive_float,
        default=DEFAULT_TIMEOUT
    )

    parser.add_argument(
        "--indent",
        help="Indent level of the printed JSON response.",
        type=positive_int,
        default=DEFAULT_INDENT
    )

    parser.add_argument(
        "--ca-native",
        help="Use the native CA store from the operating system.",
        action="store_true"
    )

    parser.add_argument(
        "--ca-certificate",
        help="Path to a bundle of PEM-formatted CA certificates.",
        type=Path
    )

    parser.add_argument(
        "--ca-directory",
        help="Path to a directory containing PEM-formatted CA certificates.",
        type=Path
    )

    register_all_commands(parser)
    args_dict = vars(parser.parse_args(args))

    # TODO(XCPNG-3032): `parsed_args.command` will always exist when subcommands are required.
    if "command" not in args_dict:
        parser.print_help(sys.stderr)
        sys.exit(2)

    command: Command = args_dict["command"]
    del args_dict["command"]

    return (command, command.build_args(args_dict))

def main() -> None:
    command, args = parse_args()
    command.run(args)
