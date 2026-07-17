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

from unittest.mock import (
    MagicMock,
    patch,
)

from xcp_storage.utils.service import (
    _EXEC_PATH_SYSTEMCTL,
    disable_and_stop_service,
    enable_and_start_service,
    escape_service_instance,
    is_service_active,
    reload_service_conf,
    restart_service,
    ServiceError,
    start_service,
    stop_service,
    try_restart_service,
)

from xcp_storage.typing import Final, List

# ==============================================================================

def test_escape_service_instance() -> None:
    assert escape_service_instance("target") == "target"
    assert escape_service_instance("target-x") == "target\\x2dx"

# ------------------------------------------------------------------------------

@patch("xcp_storage.utils.service.run_command")
class TestService:
    SERVICE_NAME: Final = "target"

    def _assert_service_command(
        self,
        mock_run_command: MagicMock,
        args: List[str],
        *,
        expected_ret_code: int,
        quiet: bool
    ) -> None:
        args.append(self.SERVICE_NAME)
        args.insert(0, _EXEC_PATH_SYSTEMCTL)
        mock_run_command.assert_called_once_with(args, expected_ret_code=expected_ret_code, quiet=quiet)

    def _assert_query_command(self, mock_run_command: MagicMock, args: List[str]) -> None:
        self._assert_service_command(mock_run_command, args, expected_ret_code=0, quiet=True)

    def _assert_action_command(self, mock_run_command: MagicMock, args: List[str]) -> None:
        self._assert_service_command(mock_run_command, args, expected_ret_code=0, quiet=False)

    def test_is_service_active(self, mock_run_command: MagicMock) -> None:
        assert is_service_active(self.SERVICE_NAME)
        self._assert_query_command(mock_run_command, ["--quiet", "is-active"])

    def test_is_service_inactive(self, mock_run_command: MagicMock) -> None:
        mock_run_command.side_effect = ServiceError("Internal error.")
        assert not is_service_active(self.SERVICE_NAME)

    def test_start_service(self, mock_run_command: MagicMock) -> None:
        start_service(self.SERVICE_NAME)
        self._assert_action_command(mock_run_command, ["start"])

    def test_stop_service(self, mock_run_command: MagicMock) -> None:
        stop_service(self.SERVICE_NAME)
        self._assert_action_command(mock_run_command, ["--quiet", "stop"])

    def test_restart_service(self, mock_run_command: MagicMock) -> None:
        restart_service(self.SERVICE_NAME)
        self._assert_action_command(mock_run_command, ["restart"])

    def test_try_restart_service(self, mock_run_command: MagicMock) -> None:
        try_restart_service(self.SERVICE_NAME)
        self._assert_action_command(mock_run_command, ["try-restart"])

    def test_enable_and_start_service(self, mock_run_command: MagicMock) -> None:
        enable_and_start_service(self.SERVICE_NAME)
        self._assert_action_command(mock_run_command, ["enable", "--now"])

    def test_disable_and_stop_service(self, mock_run_command: MagicMock) -> None:
        disable_and_stop_service(self.SERVICE_NAME)
        self._assert_action_command(mock_run_command, ["disable", "--now"])

    def test_reload_service_conf(self, mock_run_command: MagicMock) -> None:
        reload_service_conf()
        mock_run_command.assert_called_once_with([_EXEC_PATH_SYSTEMCTL, "daemon-reload"], expected_ret_code=0)
