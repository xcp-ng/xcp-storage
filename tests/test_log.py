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

import sys
from unittest.mock import MagicMock, patch

import pytest

import xcp_storage.log as log

from xcp_storage.typing import Iterator

# ==============================================================================

@pytest.fixture
def mock_logger() -> Iterator[MagicMock]:
    with patch.object(log, "_LOGGER", autospec=True) as mock_logger:
        yield mock_logger

@pytest.fixture
def mock_default_excepthook() -> Iterator[MagicMock]:
    with patch.object(sys, "__excepthook__", autospec=True) as mock_default_excepthook:
        yield mock_default_excepthook

# ------------------------------------------------------------------------------

class TestLog:
    def test_get_logger(self) -> None:
        assert log.get_logger().name == log._DEFAULT_LOGGER_NAME # noqa: SLF001
        assert log.get_logger("child").name == "child"

    def test_log_levels(self) -> None:
        assert [log.DEBUG, log.INFO, log.WARNING, log.ERROR, log.CRITICAL] == [10, 20, 30, 40, 50]

# ------------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_default_excepthook")
class TestExcepthook:
    def test_excepthook_logs_unhandled_exception(self, mock_logger: MagicMock) -> None:
        sys.excepthook(RuntimeError, RuntimeError("Boom."), None)
        mock_logger.error.assert_called_once()

    def test_excepthook_ignores_keyboard_interrupt(self, mock_logger: MagicMock) -> None:
        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
        mock_logger.error.assert_not_called()
