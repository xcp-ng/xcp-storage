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
import stat
import tempfile
from unittest.mock import patch

import pytest

from tests.utils.fd import assert_no_fd_leak, count_open_fds
from xcp_storage.utils.file import (
    close_fd,
    create_hard_link,
    create_temporary_directory,
    create_temporary_file,
    get_file_size,
    keep_files_open,
    list_temporary_paths,
    remove_directory_tree,
    remove_file,
    sync_directory,
    write_file_atomically,
)
from xcp_storage.utils.math import MIB

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

class TestGetFileSize:
    @pytest.mark.parametrize("size", [0, 1000, 4 * MIB])
    def test_size(self, file_path: Path, size: int) -> None:
        with file_path.open("wb") as file:
            file.truncate(size)
        assert get_file_size(file_path) == size

    def test_missing_file(self, file_path: Path) -> None:
        with assert_no_fd_leak(), pytest.raises(FileNotFoundError):
            get_file_size(file_path)

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

class TestWriteFileAtomically:
    def test_multiple_write_calls(self, file_path: Path, tmp_path: Path) -> None:
        write_file_atomically(file_path, "first")
        write_file_atomically(file_path, "second")
        assert file_path.read_text() == "second"
        assert list(tmp_path.iterdir()) == [file_path]

    def test_mode(self, file_path: Path) -> None:
        write_file_atomically(file_path, "data")
        assert stat.S_IMODE(file_path.stat().st_mode) == 0o644
        write_file_atomically(file_path, "data", mode=0o600)
        assert stat.S_IMODE(file_path.stat().st_mode) == 0o600

    def test_write_failure_on_directory(self, file_path: Path, tmp_path: Path) -> None:
        file_path.mkdir()
        with pytest.raises(IsADirectoryError):
            write_file_atomically(file_path, "data")
        assert list(tmp_path.iterdir()) == [file_path]

    def test_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            write_file_atomically(tmp_path / "missing" / "file", "data")

# ------------------------------------------------------------------------------

class TestSyncDirectory:
    def test_sync(self, tmp_path: Path) -> None:
        with assert_no_fd_leak():
            sync_directory(tmp_path)

    def test_missing_directory(self, tmp_path: Path) -> None:
        with assert_no_fd_leak(), pytest.raises(FileNotFoundError):
            sync_directory(tmp_path / "missing")

    def test_not_a_directory(self, file_path: Path) -> None:
        file_path.write_bytes(b"")
        with assert_no_fd_leak(), pytest.raises(NotADirectoryError):
            sync_directory(file_path)

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

# ------------------------------------------------------------------------------

class TestRemoveDirectoryTree:
    @pytest.mark.parametrize("missing_ok", [False, True])
    def test_remove(self, tmp_path: Path, *, missing_ok: bool) -> None:
        # Create directory tree.
        path = tmp_path / "tree"
        (path / "directory").mkdir(parents=True)
        (path / "directory" / "file").write_text("data")

        # The target of a symbolic link inside it must be preserved.
        target_path = tmp_path / "target"
        target_path.mkdir()
        (target_path / "file").write_text("data")
        (path / "link").symlink_to(target_path)

        remove_directory_tree(path, missing_ok=missing_ok)
        assert not path.exists()
        assert (target_path / "file").read_text() == "data"

    def test_remove_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            remove_directory_tree(tmp_path / "missing")

    def test_remove_missing_directory_ok(self, tmp_path: Path) -> None:
        remove_directory_tree(tmp_path / "missing", missing_ok=True)

# ------------------------------------------------------------------------------

class TestTemporaryFile:
    def test_file(self, file_path: Path, tmp_path: Path) -> None:
        with create_temporary_file(file_path) as tmp_file:
            tmp_file_path = Path(tmp_file.name)
            assert tmp_file_path.parent == tmp_path
            assert stat.S_IMODE(tmp_file_path.stat().st_mode) == 0o600
            assert list_temporary_paths(file_path) == [tmp_file_path]

        assert list(tmp_path.iterdir()) == []

    def test_renamed_file(self, file_path: Path, tmp_path: Path) -> None:
        with create_temporary_file(file_path) as tmp_file:
            tmp_file.write("data")
            tmp_file.flush()
            Path(tmp_file.name).replace(file_path)
        assert file_path.read_text() == "data"
        assert list(tmp_path.iterdir()) == [file_path]

    def test_file_on_failure(self, file_path: Path, tmp_path: Path) -> None:
        with pytest.raises(KeyboardInterrupt), create_temporary_file(file_path):
            raise KeyboardInterrupt
        assert list(tmp_path.iterdir()) == []

class TestTemporaryDirectory:
    def test_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "directory"
        with create_temporary_directory(path) as tmp_dir_path:
            assert tmp_dir_path.is_dir() and tmp_dir_path.parent == tmp_path
            assert stat.S_IMODE(tmp_dir_path.stat().st_mode) == 0o700
            assert list_temporary_paths(path) == [tmp_dir_path]
            (tmp_dir_path / "content").touch()

        assert list(tmp_path.iterdir()) == []

    def test_system_directory(self) -> None:
        # Without path: in the temporary directory of the system.
        with create_temporary_directory() as tmp_dir_path:
            assert tmp_dir_path.is_dir() and tmp_dir_path.parent == Path(tempfile.gettempdir())
        assert not tmp_dir_path.exists()

    def test_renamed_directory(self, file_path: Path, tmp_path: Path) -> None:
        with create_temporary_directory(file_path) as tmp_dir_path:
            (tmp_dir_path / "content").touch()
            tmp_dir_path.replace(file_path)

        assert list(tmp_path.iterdir()) == [file_path]
        assert list(file_path.iterdir()) == [file_path / "content"]

    def test_directory_on_failure(self, file_path: Path, tmp_path: Path) -> None:
        with pytest.raises(KeyboardInterrupt), create_temporary_directory(file_path) as tmp_dir_path:
            (tmp_dir_path / "content").touch()
            raise KeyboardInterrupt
        assert list(tmp_path.iterdir()) == []

    def test_unique(self, file_path: Path) -> None:
        with create_temporary_directory(file_path) as tmp_dir_path, \
             create_temporary_directory(file_path) as other_tmp_dir_path:
            assert tmp_dir_path != other_tmp_dir_path
            assert list_temporary_paths(file_path) == sorted([tmp_dir_path, other_tmp_dir_path])

class TestTemporaryPathList:
    def test_directory_list(self, file_path: Path, tmp_path: Path) -> None:
        file_path.touch()

        # Names close to those of the temporary paths of `file_path`, built by hand.
        for name in (".file.tmp.old", "file.l3ft0v3r.tmp"): # nosemgrep: python-enforce-temporary-path-helpers
            (tmp_path / name).touch()

        with create_temporary_directory(tmp_path / "file2"), create_temporary_directory(tmp_path / "other"), \
                create_temporary_directory(file_path) as tmp_dir_path:
            assert list_temporary_paths(file_path) == [tmp_dir_path]

# ------------------------------------------------------------------------------

class TestKeepFilesOpen:
    def test_keep_open(self, tmp_path: Path) -> None:
        read_path = tmp_path / "read"
        write_path = tmp_path / "write"

        read_path.write_text("data")
        write_path.write_text("data")

        with keep_files_open([(read_path, False), (write_path, True)]):
            assert (count_open_fds(read_path), count_open_fds(write_path)) == (1, 1)
        assert (count_open_fds(read_path), count_open_fds(write_path)) == (0, 0)

    def test_write_mode(self, tmp_path: Path) -> None:
        # A directory opens for reading only.
        with keep_files_open([(tmp_path, False)]):
            assert count_open_fds(tmp_path) == 1

        with assert_no_fd_leak(), pytest.raises(IsADirectoryError), keep_files_open([(tmp_path, True)]):
            pass

    def test_failure_closes_open_files(self, file_path: Path, tmp_path: Path) -> None:
        open_path = tmp_path / "open"
        open_path.write_text("data")

        with assert_no_fd_leak(), pytest.raises(FileNotFoundError), \
                keep_files_open([(open_path, False), (file_path, False)]):
            pass
