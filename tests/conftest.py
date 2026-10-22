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
import shutil

import pytest

from xcp_storage.utils.process import CommandError, run_internal_command

from xcp_storage.typing import Final, List

# ==============================================================================

PROJECT_PATH: Final = Path(__file__).parents[1]

# The usual CMake build directory of the project: it's initialized (if necessary),
# reused and never cleaned by the tests.
PROJECT_BUILD_PATH: Final = PROJECT_PATH / "build"

# Nothing is installed on the system by the tests, but the configuration must not
# depend on system paths: the install directories are inside the build directory.
_PROJECT_INSTALL_PATH: Final = PROJECT_BUILD_PATH / "install"
_PROJECT_SYSTEMD_UNIT_PATH: Final = _PROJECT_INSTALL_PATH / "lib" / "systemd" / "system"

# `cmake` configures the whole project and `pkg-config` is required by its `CMakeLists.txt`.
_PROJECT_BUILD_TOOLS: Final = ("cmake", "pkg-config")

# ------------------------------------------------------------------------------

def _run_build_command(command: List[str]) -> None:
    try:
        stdout, stderr, ret_code = run_internal_command(command, simple=False)
    except CommandError as e:
        pytest.fail(f"Command `{' '.join(command)}` failed: `{e.reason}`.", pytrace=False)

    if ret_code != 0:
        # Some build tools (`ninja`...) report their errors on stdout.
        pytest.fail(f"Command `{' '.join(command)}` failed:\n{stdout}{stderr}", pytrace=False)

# ------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_build_path() -> Path:
    """
    Directory of a build of the whole project with CMake, done once for the whole session.
    Tests that need a built artifact (daemon for example) must use it.
    """

    for build_tool in _PROJECT_BUILD_TOOLS:
        if not shutil.which(build_tool):
            pytest.skip(f"`{build_tool}` is required to build the project.")

    _run_build_command([
        "cmake",
        "-S", str(PROJECT_PATH),
        "-B", str(PROJECT_BUILD_PATH),
        f"-DCMAKE_INSTALL_PREFIX:PATH={_PROJECT_INSTALL_PATH}",
        f"-DSYSTEMD_SYSTEM_UNIT_DIR:PATH={_PROJECT_SYSTEMD_UNIT_PATH}"
    ])
    _run_build_command(["cmake", "--build", str(PROJECT_BUILD_PATH)])

    return PROJECT_BUILD_PATH
