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

import errno
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from xcp_storage.utils.file import close_fd, create_hard_link, remove_file

# ==============================================================================

@pytest.fixture
def file_path(tmp_path: Path) -> Path:
    # Not created.
    return tmp_path / "file"

# ------------------------------------------------------------------------------

class TestCloseFd:
    def test_close(self) -> None:
        read_fd, write_fd = os.pipe()
        try:
            close_fd(read_fd)
            with pytest.raises(OSError, match="Bad file descriptor") as exc_info:
                os.fstat(read_fd)
            assert exc_info.value.errno == errno.EBADF
        finally:
            close_fd(write_fd)

    def test_already_closed_fd_is_ignored(self) -> None:
        read_fd, write_fd = os.pipe()
        close_fd(read_fd)
        close_fd(read_fd)
        close_fd(write_fd)

    @pytest.mark.parametrize("error_code", [errno.EBADF, errno.EIO, errno.EINTR])
    def test_error_is_ignored(self, error_code: int) -> None:
        with patch("os.close", side_effect=OSError(error_code), autospec=True) as mock_close:
            close_fd(42)
        mock_close.assert_called_once_with(42)

# ------------------------------------------------------------------------------

class TestCreateHardLink:
    def test_create(self, tmp_path: Path) -> None:
        target_path = tmp_path / "target"
        target_path.write_text("data")

        link_path = tmp_path / "link"

        create_hard_link(link_path, target_path)

        assert link_path.read_text() == "data"
        assert link_path.stat().st_ino == target_path.stat().st_ino
        assert target_path.stat().st_nlink == 2

    def test_existing_path(self, tmp_path: Path) -> None:
        target_path = tmp_path / "target"
        target_path.write_text("data")

        link_path = tmp_path / "link"
        link_path.write_text("other")

        with pytest.raises(FileExistsError):
            create_hard_link(link_path, target_path)

        assert target_path.read_text() == "data"
        assert link_path.read_text() == "other"

    def test_missing_target(self, tmp_path: Path) -> None:
        link_path = tmp_path / "link"
        with pytest.raises(FileNotFoundError):
            create_hard_link(link_path, tmp_path / "target")
        assert not link_path.exists()

# ------------------------------------------------------------------------------

class TestRemoveFile:
    @pytest.mark.parametrize("missing_ok", [False, True])
    def test_remove(self, file_path: Path, *, missing_ok: bool) -> None:
        file_path.write_text("data")
        remove_file(file_path, missing_ok=missing_ok)
        assert not file_path.exists()

    def test_remove_symlink_only(self, tmp_path: Path) -> None:
        target_path = tmp_path / "target"
        target_path.write_text("data")

        link_path = tmp_path / "link"
        link_path.symlink_to(target_path)

        remove_file(link_path)

        assert not link_path.is_symlink()
        assert target_path.read_text() == "data"

    def test_remove_missing_file(self, file_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            remove_file(file_path)

    def test_remove_missing_file_ok(self, file_path: Path) -> None:
        remove_file(file_path, missing_ok=True)

    @pytest.mark.parametrize("missing_ok", [False, True])
    def test_remove_directory(self, tmp_path: Path, *, missing_ok: bool) -> None:
        with pytest.raises(IsADirectoryError):
            remove_file(tmp_path, missing_ok=missing_ok)
        assert tmp_path.is_dir()
