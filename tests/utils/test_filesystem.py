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
from unittest.mock import _Call, call, MagicMock, patch

import pytest

from tests.utils.exception import raises_exactly
from xcp_storage.utils.filesystem import (
    _EXEC_PATH_BLKID,
    _EXEC_PATH_MKFS_EXT4,
    _EXEC_PATH_MOUNT,
    _EXEC_PATH_UMOUNT,
    _FILESYSTEM_COMMAND_TIMEOUT,
    create_ext4_filesystem,
    FilesystemError,
    FilesystemTimeoutError,
    get_filesystem_type,
    is_mount_point,
    mount_filesystem,
    unmount_filesystem,
)
from xcp_storage.utils.process import CommandError, CommandResult, CommandTimeoutError

from xcp_storage.typing import Final, Iterator, Optional

# ==============================================================================

_FILESYSTEM_MODULE: Final = get_filesystem_type.__module__

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_run_command() -> Iterator[MagicMock]:
    with patch(f"{_FILESYSTEM_MODULE}.run_command", autospec=True) as mock_run_command:
        yield mock_run_command

@pytest.fixture
def mock_is_mount_point() -> Iterator[MagicMock]:
    with patch(f"{_FILESYSTEM_MODULE}.is_mount_point", autospec=True) as mock_is_mount_point:
        yield mock_is_mount_point

@pytest.fixture
def device_path(tmp_path: Path) -> Path:
    # A block device (a file is enough for the mocked commands).
    path = tmp_path / "drbd1000"
    path.touch()
    return path

# ------------------------------------------------------------------------------

def create_fs_run_command_call(*args: str, timeout: Optional[float] = _FILESYSTEM_COMMAND_TIMEOUT) -> _Call:
    return call(list(args), simple=False, timeout=timeout)

# ------------------------------------------------------------------------------

class TestGetFilesystemType:
    def test_filesystem(self, mock_run_command: MagicMock, device_path: Path) -> None:
        mock_run_command.return_value = CommandResult(stdout="ext4\n")
        assert get_filesystem_type(device_path) == "ext4"
        assert mock_run_command.call_args_list == [
            create_fs_run_command_call(_EXEC_PATH_BLKID, "-p", "-o", "value", "-s", "TYPE", str(device_path))
        ]

    def test_no_filesystem(self, mock_run_command: MagicMock, device_path: Path) -> None:
        # Exit code 2: nothing found.
        mock_run_command.return_value = CommandResult(ret_code=2)
        assert get_filesystem_type(device_path) is None

    def test_missing_device(self, mock_run_command: MagicMock, tmp_path: Path) -> None:
        path = tmp_path / "drbd1001"
        with raises_exactly(FileNotFoundError, f"Block device `{path}` does not exist."):
            get_filesystem_type(path)
        mock_run_command.assert_not_called()

    def test_failure(self, mock_run_command: MagicMock, device_path: Path) -> None:
        stderr = f"error: {device_path}: Wrong medium type"
        mock_run_command.return_value = CommandResult(stderr=f"{stderr}\n", ret_code=4)
        with raises_exactly(FilesystemError, f"Command `blkid` failed: `{stderr}`.") as exc_info:
            get_filesystem_type(device_path)
        assert exc_info.value.code == 4

# ------------------------------------------------------------------------------

class TestCreateExt4Filesystem:
    def test_create(self, mock_run_command: MagicMock, device_path: Path) -> None:
        # Without discard by default, and without timeout.
        mock_run_command.return_value = CommandResult()
        create_ext4_filesystem(device_path)
        assert mock_run_command.call_args_list == [
            create_fs_run_command_call(_EXEC_PATH_MKFS_EXT4, "-q", "-E", "nodiscard", str(device_path), timeout=None)
        ]

    def test_create_with_discard(self, mock_run_command: MagicMock, device_path: Path) -> None:
        mock_run_command.return_value = CommandResult()
        create_ext4_filesystem(device_path, discard=True)
        assert mock_run_command.call_args_list == [
            create_fs_run_command_call(_EXEC_PATH_MKFS_EXT4, "-q", "-E", "discard", str(device_path), timeout=None)
        ]

    def test_failure(self, mock_run_command: MagicMock, device_path: Path) -> None:
        stderr = f"mkfs.ext4: Device size reported to be zero.  {device_path}"
        mock_run_command.return_value = CommandResult(stderr=f"{stderr}\n", ret_code=1)
        with raises_exactly(FilesystemError, f"Command `mkfs.ext4` failed: `{stderr}`.") as exc_info:
            create_ext4_filesystem(device_path)
        assert exc_info.value.code == 1

    def test_command_error(self, mock_run_command: MagicMock, device_path: Path) -> None:
        mock_run_command.side_effect = CommandError(None, "mkfs.ext4", "No such file or directory")
        with raises_exactly(FilesystemError, "Failed to run command `mkfs.ext4`: `No such file or directory`."):
            create_ext4_filesystem(device_path)

# ------------------------------------------------------------------------------

class TestIsMountPoint:
    def test_mount_point(self) -> None:
        # The root directory is always a mount point.
        assert is_mount_point(Path("/"))

    def test_not_mount_point(self, tmp_path: Path) -> None:
        assert not is_mount_point(tmp_path)
        assert not is_mount_point(tmp_path / "missing")

class TestMountFilesystem:
    def test_mount(self, mock_run_command: MagicMock, device_path: Path, tmp_path: Path) -> None:
        mock_run_command.return_value = CommandResult()
        mount_filesystem(device_path, tmp_path)
        assert mock_run_command.call_args_list == [
            create_fs_run_command_call(_EXEC_PATH_MOUNT, "-w", str(device_path), str(tmp_path))
        ]

    @pytest.mark.parametrize("lazy", [False, True], ids=["plain", "lazy"])
    def test_unmount(
        self, mock_run_command: MagicMock, mock_is_mount_point: MagicMock, tmp_path: Path, *, lazy: bool
    ) -> None:
        mock_run_command.return_value = CommandResult()
        mock_is_mount_point.return_value = True
        unmount_filesystem(tmp_path, lazy=lazy)
        assert mock_run_command.call_args_list == [
            create_fs_run_command_call(_EXEC_PATH_UMOUNT, *(["-l"] if lazy else []), str(tmp_path))
        ]

    def test_mount_timeout(self, mock_run_command: MagicMock, device_path: Path, tmp_path: Path) -> None:
        mock_run_command.side_effect = CommandTimeoutError(None, "", "")
        with raises_exactly(
            FilesystemTimeoutError, f"Command `mount` did not end within {_FILESYSTEM_COMMAND_TIMEOUT} second(s)."
        ):
            mount_filesystem(device_path, tmp_path)

    def test_unmount_not_mounted(
        self, mock_run_command: MagicMock, mock_is_mount_point: MagicMock, tmp_path: Path
    ) -> None:
        mock_is_mount_point.return_value = False
        unmount_filesystem(tmp_path)
        mock_run_command.assert_not_called()
