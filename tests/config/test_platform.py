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
from unittest.mock import patch

import pytest

from xcp_storage.config.platform import get_exec_path, get_os_ids

from xcp_storage.typing import Final, Iterator, Tuple

# ==============================================================================

@pytest.fixture(autouse=True)
def clear_os_ids_cache() -> Iterator[None]:
    get_os_ids.cache_clear()
    yield
    get_os_ids.cache_clear()

@pytest.fixture
def os_release_path(tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "os-release"
    with patch("xcp_storage.config.platform._OS_RELEASE_PATH", str(path)):
        yield path

# ------------------------------------------------------------------------------

class TestGetOsIds:
    @pytest.mark.parametrize(("content", "expected"), [
        ("ID=alpine\n", ("alpine",)),
        ('NAME="Ubuntu"\nID=ubuntu\nID_LIKE=debian\n', ("ubuntu", "debian")),
        ('ID="rhel"\nID_LIKE="fedora centos"\n', ("rhel", "fedora", "centos")),
        ("NAME=Foo\n", ()),
    ])
    def test_parsing(self, os_release_path: Path, content: str, expected: Tuple[str, ...]) -> None:
        os_release_path.write_text(content)
        assert get_os_ids() == expected

    def test_without_os_release_file(self, os_release_path: Path) -> None:
        assert not os_release_path.exists()
        assert get_os_ids() == ()

    def test_os_release_file_is_cached(self, os_release_path: Path) -> None:
        os_release_path.write_text("ID=alpine\n")
        expected = get_os_ids()
        os_release_path.write_text("ID=ubuntu\n")
        assert get_os_ids() == expected

# ------------------------------------------------------------------------------

class TestGetExecPath:
    DEFAULT_PATH: Final = "/opt/default/tool"
    ALT_PATH: Final = "/opt/alt/tool"
    BY_OS_ID: Final = {"debian": ALT_PATH}

    def test_with_mapping_id_match(self, os_release_path: Path) -> None:
        os_release_path.write_text("ID=debian\nID_LIKE=unknown\n")
        assert get_exec_path(self.DEFAULT_PATH, self.BY_OS_ID) == self.ALT_PATH

    def test_with_mapping_id_like_match(self, os_release_path: Path) -> None:
        os_release_path.write_text("ID=ubuntu\nID_LIKE=debian\n")
        assert get_exec_path(self.DEFAULT_PATH, self.BY_OS_ID) == self.ALT_PATH

    def test_without_mapping_match(self, os_release_path: Path) -> None:
        os_release_path.write_text("ID=alpine\n")
        assert get_exec_path(self.DEFAULT_PATH, self.BY_OS_ID) == self.DEFAULT_PATH

    def test_without_os_release_file(self, os_release_path: Path) -> None:
        assert not os_release_path.exists()
        assert get_exec_path(self.DEFAULT_PATH, self.BY_OS_ID) == self.DEFAULT_PATH
