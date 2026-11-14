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

import contextlib
import os
from pathlib import Path, PurePath
import shutil
import tempfile

from xcp_storage.typing import Final, IO, Iterator, List, Optional

# ==============================================================================

# `select` only supports the descriptors below this value.
FD_SETSIZE: Final = 1024

# Suffix of the temporary files and directories created beside a path.
_TEMPORARY_FILE_SUFFIX: Final = ".tmp"

# ------------------------------------------------------------------------------

def _get_temporary_file_prefix(path: PurePath) -> str:
    return f".{path.name}."

# ------------------------------------------------------------------------------

def close_fd(fd: int) -> None:
    """
    Close a file descriptor, ignoring the errors.

    Nothing useful can be done if `close` fails (on Linux the descriptor is released anyway),
    and the error must not hide the exception being handled or break a release.
    """
    with contextlib.suppress(OSError):
        os.close(fd)

# ------------------------------------------------------------------------------

def create_hard_link(path: PurePath, target_path: PurePath) -> None:
    """
    Create `path` as a hard link to the file `target_path`.
    `FileExistsError` is raised if `path` exists.
    """

    # TODO(XCPNG-3032): Use `Path.hardlink_to` in python 3.10.
    os.link(target_path, path)

# ------------------------------------------------------------------------------

def write_file_atomically(path: PurePath, text: str, *, mode: int = 0o644) -> None:
    """
    Write `text` in the file `path` with the permissions `mode`, replaced at once: a reader sees the previous content or
    the new one, never a part of it, even after a crash.
    """

    with create_temporary_file(path) as tmp_file:
        tmp_file.write(text)
        tmp_file.flush()

        fd = tmp_file.fileno()
        os.fchmod(fd, mode)
        os.fsync(fd)

        Path(tmp_file.name).replace(path)

def remove_file(path: PurePath, *, missing_ok: bool = False) -> None:
    """
    Remove a file `path`. Cannot remove a directory.
    `FileNotFoundError` is raised if it does not exist, unless `missing_ok`.
    """

    # TODO(XCPNG-3032): Use `Path.unlink(missing_ok=...)` in python 3.8.
    try:
        Path(path).unlink()
    except FileNotFoundError:
        if not missing_ok:
            raise

# ------------------------------------------------------------------------------

@contextlib.contextmanager
def create_temporary_file(path: PurePath) -> Iterator[IO[str]]:
    """
    Create and open for writing a new text file beside `path`, in the same file system, readable and writable by its
    owner only: `.<name>.<random>.tmp`, never shared with another caller.
    Removed at the exit, even on failure, unless renamed meanwhile.
    """

    # TODO(XCPNG-3032): Use `delete=True` alone in python 3.12: before, closing a renamed file raises
    # `FileNotFoundError`.
    with tempfile.NamedTemporaryFile(
        "w", prefix=_get_temporary_file_prefix(path), suffix=_TEMPORARY_FILE_SUFFIX, dir=str(path.parent), delete=False
    ) as tmp_file:
        try:
            yield tmp_file
        finally:
            remove_file(Path(tmp_file.name), missing_ok=True)

@contextlib.contextmanager
def create_temporary_directory(path: Optional[PurePath] = None) -> Iterator[Path]:
    """
    Create a new directory accessible by its owner only, never shared with another caller: beside `path`, in the same
    file system (`.<name>.<random>.tmp`), or in the temporary directory of the system without `path`.
    Removed with its content at the exit, even on failure, unless renamed meanwhile.
    """

    if path is None:
        tmp_dir_path = Path(tempfile.mkdtemp())
    else:
        tmp_dir_path = Path(tempfile.mkdtemp(
            prefix=_get_temporary_file_prefix(path), suffix=_TEMPORARY_FILE_SUFFIX, dir=str(path.parent)
        ))

    try:
        yield tmp_dir_path
    finally:
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(str(tmp_dir_path))

def list_temporary_paths(path: PurePath) -> List[Path]:
    """
    Return the temporary files and directories created beside `path` (e.g. left by a crash).
    """

    prefix = _get_temporary_file_prefix(path)
    return [
        temporary_path for temporary_path in sorted(Path(path.parent).iterdir())
        if temporary_path.name.startswith(prefix) and temporary_path.name.endswith(_TEMPORARY_FILE_SUFFIX)
    ]
