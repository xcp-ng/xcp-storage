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
import json
import sys

import xcp_storage.log as log
from xcp_storage.utils.json import JsonDict, JsonList
from xcp_storage_cli.args import GlobalArgs, str_or_stdin
from xcp_storage_cli.commands.command import Command

from xcp_storage.typing import Any, Dict, Optional, override, Union

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

@dataclass
class LlcallArgs(GlobalArgs):
    func: str
    params: Optional[str]

# ------------------------------------------------------------------------------

class LlcallCommand(Command[LlcallArgs]):
    @property
    @override
    def name(self) -> str:
        return "llcall"

    @property
    @override
    def help(self) -> str:
        return "Low-level JSON-RPC function call."

    @override
    def register(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("func", help="Name of the RPC function to call.")

        parser.add_argument(
            "params",
            help="JSON-serialized parameters to call the RPC function with. Pass `-` to capture params from stdin.",
            type=str_or_stdin,
            nargs="?"
        )

    @override
    def build_args(self, args_dict: Dict[str, Any]) -> LlcallArgs:
        return LlcallArgs(**args_dict)

    @override
    def run(self, args: LlcallArgs) -> None:
        params: Union[JsonList, JsonDict, None] = None

        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON-RPC `params` object: %s", e)
                sys.exit(1)

        rpc_client = args.create_rpc_client()

        try:
            response = rpc_client.call(args.func, params)
        except Exception as e:
            logger.error("RPC call failed: %s", e)
            sys.exit(1)

        try:
            print(json.dumps(response, indent=args.indent or None))  # noqa: T201
        except (TypeError, ValueError):
            # It looks like `json.dumps` failed. Print the raw response regardless.
            print(response)  # noqa: T201
