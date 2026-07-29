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

from abc import ABC, abstractmethod
import argparse

from xcp_storage_cli.args import GlobalArgs

from xcp_storage.typing import Any, Dict, Generic, TypeVar

ArgsT = TypeVar("ArgsT", bound=GlobalArgs)

# ==============================================================================

class Command(ABC, Generic[ArgsT]):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def help(self) -> str:
        pass

    @abstractmethod
    def register(self, parser: argparse.ArgumentParser) -> None:
        pass

    @abstractmethod
    def build_args(self, args_dict: Dict[str, Any]) -> ArgsT:
        pass

    @abstractmethod
    def run(self, args: ArgsT) -> None:
        pass
