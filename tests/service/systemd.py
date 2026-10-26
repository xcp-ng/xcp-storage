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
from functools import lru_cache
import os
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

import pytest

from xcp_storage.config.platform import RUNTIME_DIR_PATH
from xcp_storage.utils.process import CommandError, run_command
from xcp_storage.utils.service import _EXEC_PATH_SYSTEMCTL

from xcp_storage.typing import (
    Final,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
)

# ==============================================================================
# Helpers to run the tests with `systemd` and without installation: a manager
# runs a copy of a unit file, adapted to the paths of the test, linked in
# its runtime directory.
# The current `systemd` config is used when there is one (no root required),
# a fallback is used when no config is found and if the tests are executed in
# a root context.
# ==============================================================================

# Directories of the runtime units, relative to the runtime directory of the manager.
_SYSTEM_RUNTIME_UNIT_DIR_PATH: Final = Path("systemd/system")
_USER_RUNTIME_UNIT_DIR_PATH: Final = Path("systemd/user")

# Maximum duration of a `systemctl` call.
# As a reminder: a `stop` waits for the units, bounded by their `TimeoutStopSec=`.
# A reasonable delay must therefore be used here.
_SYSTEMCTL_TIMEOUT: Final = 30.0

# Regex used to remove specific fields of a service. Otherwise we can't always test in user mode.
_UNIT_IGNORED_FIELDS_REGEX: Final = re.compile(r"^(PrivateTmp|ProtectHome|ProtectSystem)=.*\n", re.MULTILINE)

# Program of a command line (`ExecStart=`...), after the optional special prefixes.
_UNIT_EXEC_PROGRAM_REGEX: Final = re.compile(r"^(Exec\w+=[-@:+!]*)(\S+)", re.MULTILINE)

# ------------------------------------------------------------------------------

def _get_systemctl_manager_option(*, user_mode: bool) -> str:
    """
    Return the option of `systemctl` selecting the manager of
    the current user or the system one.
    """

    return "--user" if user_mode else "--system"

def _run_systemctl_command(args: List[str], *, user_mode: bool, quiet: bool = False) -> str:
    return run_command(
        [_EXEC_PATH_SYSTEMCTL, _get_systemctl_manager_option(user_mode=user_mode), *args],
        expected_ret_code=0,
        quiet=quiet,
        timeout=_SYSTEMCTL_TIMEOUT,
    )

def _get_systemd_environment(*, user_mode: bool) -> Optional[str]:
    """
    Return the environment of the `systemd`, or `None` if it cannot be reached.
    For example without session bus we have: "Failed to get D-Bus connection".
    """

    try:
        return _run_systemctl_command(["show-environment"], user_mode=user_mode, quiet=True)
    except CommandError:
        return None

# ------------------------------------------------------------------------------

class ServiceManager(NamedTuple):
    # Indicate the systemd mode: `user` or `system`.
    user_mode: bool

    # What `%t` is in its units.
    runtime_dir_path: Path

    @contextlib.contextmanager
    def registered_service(self, unit_path: Path, *, executable_paths: Sequence[Path] = ()) -> Iterator[str]:
        """
        Make a copy of the unit `unit_path`, and yields its name:
        - It overrides an installed unit of the same name until the end.
        - The programs of the command lines (`ExecStart=`...) named like one of `executable_paths` (built programs of
          the project) are replaced by them: the installed paths of the unit do not need to be known. Runtime files
          MUST use `%t`, so that the unit works for both managers.
        - On exit, the unit is stopped and removed. The instances of a template must be stopped by the caller: they are
          started during the tests, so their names are not known here, and stopping all of them by pattern is not
          possible because, the copy overrides the installed template of the same name: its already
          running instances (production ones) match too.
        """

        # 1. Replace executables paths.
        executable_paths_by_name = {path.name: path for path in executable_paths}
        replaced_executable_names = set()

        def replace_program_field(match: "re.Match[str]") -> str:
            name = Path(match.group(2)).name
            if name not in executable_paths_by_name:
                return match.group(0)
            replaced_executable_names.add(name)
            return match.group(1) + str(executable_paths_by_name[name])

        unit_content = _UNIT_EXEC_PROGRAM_REGEX.sub(
            replace_program_field,
            _UNIT_IGNORED_FIELDS_REGEX.sub("", unit_path.read_text())
        )
        # The unit must run the given programs: fail if one is missing.
        assert replaced_executable_names == set(executable_paths_by_name), f"Programs not found in `{unit_path}`."

        # 2. Create unit.
        unit_name = unit_path.name
        is_unit_template = "@." in unit_name

        with contextlib.ExitStack() as stack:
            if not is_unit_template or self._can_link_template():
                # `link` makes the unit known to the manager without copying it in a specific config directory.
                tmp_dir_path = stack.enter_context(tempfile.TemporaryDirectory())
                unit_copy_path = Path(tmp_dir_path) / unit_name
                unit_copy_path.write_text(unit_content)
                self._link_runtime_unit(unit_copy_path)
                stack.callback(self._unlink_runtime_unit, unit_name)
            else:
                # Fallback for old `systemd` (219) that cannot link a template: the copy is put where
                # `link --runtime` would put its link.
                runtime_unit_path = self._get_runtime_unit_dir_path() / unit_name
                assert not runtime_unit_path.exists(), f"`{runtime_unit_path}` already exists."

                runtime_unit_path.parent.mkdir(parents=True, exist_ok=True)
                runtime_unit_path.write_text(unit_content)
                self._reload_units()

                stack.callback(self._reload_units)
                stack.callback(runtime_unit_path.unlink)

            if not is_unit_template:
                stack.callback(self._run_systemctl_command, ["stop", unit_name])

            yield unit_name

    def _get_runtime_unit_dir_path(self) -> Path:
        unit_dir_path = _USER_RUNTIME_UNIT_DIR_PATH if self.user_mode else _SYSTEM_RUNTIME_UNIT_DIR_PATH
        return self.runtime_dir_path / unit_dir_path

    def _run_systemctl_command(self, args: List[str], *, quiet: bool = False) -> str:
        return _run_systemctl_command(args, user_mode=self.user_mode, quiet=quiet)

    def _link_runtime_unit(self, unit_path: Path, *, quiet: bool = False) -> None:
        self._run_systemctl_command(["link", "--runtime", str(unit_path)], quiet=quiet)

    def _unlink_runtime_unit(self, unit_name: str) -> None:
        self._run_systemctl_command(["disable", "--runtime", unit_name])

    def _reload_units(self) -> None:
        self._run_systemctl_command(["daemon-reload"])

    # Cached for all the managers: it only depends on the version of `systemd`.
    @classmethod
    @lru_cache(maxsize=None)
    def _can_link_template(cls) -> bool:
        """
        Return whether `systemd` can `link` a template, probed with the detected manager.
        Old `systemd` versions (219) cannot: "missing the instance name".
        """

        service_manager: ServiceManager = _get_service_manager()

        probe_unit_name = "xcp-storage-link-probe@.service"

        with tempfile.TemporaryDirectory() as tmp_dir_path:
            probe_unit_path = Path(tmp_dir_path) / probe_unit_name
            probe_unit_path.write_text("[Service]\nExecStart=/bin/true\n")
            try:
                service_manager._link_runtime_unit(probe_unit_path, quiet=True)
            except CommandError as e:
                if "missing the instance name" in e.reason:
                    return False
                raise

        service_manager._unlink_runtime_unit(probe_unit_name)
        return True

# ------------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _get_service_manager() -> ServiceManager:
    """
    Return the manager of the current user if any, else the system manager when running as root.
    Skip the test when none is available (e.g. in a container).
    """

    environment = _get_systemd_environment(user_mode=True)
    if environment is not None:
        for line in environment.splitlines():
            name, _, value = line.partition("=")
            if name == "XDG_RUNTIME_DIR":
                return ServiceManager(user_mode=True, runtime_dir_path=Path(value))
        pytest.fail("`XDG_RUNTIME_DIR` is not set in the environment of the user manager.")

    # Fallback: use root when available.
    if os.geteuid() == 0 and _get_systemd_environment(user_mode=False) is not None:
        return ServiceManager(user_mode=False, runtime_dir_path=RUNTIME_DIR_PATH)

    pytest.skip("A `systemd` with user or system mode, or running as root, is required.")

# ------------------------------------------------------------------------------

@pytest.fixture
def service_manager(tmp_path: Path) -> Iterator[ServiceManager]:
    """
    Service manager wrapper used to run the tests.
    """

    service_manager = _get_service_manager()

    wrapper_path = tmp_path / "systemctl"
    manager_option = _get_systemctl_manager_option(user_mode=service_manager.user_mode)
    wrapper_path.write_text(f'#!/bin/sh\nexec "{_EXEC_PATH_SYSTEMCTL}" {manager_option} "$@"\n')
    wrapper_path.chmod(0o700)

    with patch("xcp_storage.utils.service._EXEC_PATH_SYSTEMCTL", str(wrapper_path)):
        yield service_manager
