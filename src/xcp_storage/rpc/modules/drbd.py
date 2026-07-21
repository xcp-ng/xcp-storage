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

from dataclasses import asdict

from xcp_storage.backends.drbd import Drbd, DrbdVolumeSpecifier
from xcp_storage.rpc.dispatcher import ApiDispatcher
from xcp_storage.utils.json import JsonDict

from xcp_storage.typing import (
    assert_type,
    cast,
    Dict,
    List,
    MYPY,
    PYREFLY,
    Union,
)

# ==============================================================================

@ApiDispatcher.method
def get_openers(resource_name: str, volume_number: int) -> List[JsonDict]:
    openers = [asdict(opener) for opener in Drbd.get_local_openers(resource_name, volume_number)]
    # Some linters, such as pyrefly, may struggle to convert a type to a recursive type.
    # We therefore perform a static check (so that it's validated by linters) and we cast it explicitly.
    if PYREFLY and not MYPY:
        assert_type(openers, List[Dict[str, Union[int, str, List[str]]]])
    return cast(List[JsonDict], openers)

@ApiDispatcher.method
def get_openers_from_specifiers(volume_specifiers: List[str]) -> JsonDict:
    openers = {}
    for volume_specifier_str in volume_specifiers:
        volume_specifier = DrbdVolumeSpecifier.parse(volume_specifier_str)
        openers[volume_specifier_str] = get_openers(volume_specifier.resource_name, volume_specifier.volume_number)

    return cast(JsonDict, openers)
