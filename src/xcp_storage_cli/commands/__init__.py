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

from xcp_storage_cli.commands.command import Command

from xcp_storage.typing import Final, List

# ==============================================================================

_ALL_COMMANDS: Final[List[Command]] = []

# ------------------------------------------------------------------------------

def register_all_commands(parser: argparse.ArgumentParser) -> None:
    # TODO(XCPNG-3032): Add `required=True`.
    subparsers = parser.add_subparsers()

    for command in _ALL_COMMANDS:
        command_parser = subparsers.add_parser(command.name, help=command.help)

        command.register(command_parser)
        command_parser.set_defaults(command=command)
