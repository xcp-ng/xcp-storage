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

from unittest.mock import MagicMock, Mock, patch

from xcp_storage.utils.sync import wait_for_condition

# ==============================================================================

@patch("time.sleep")
class TestWaitForCondition:
    def test_success(self, mock_sleep: MagicMock) -> None:
        func = Mock(return_value=True)
        assert wait_for_condition(func, timeout=5.0, interval=0.1)
        func.assert_called_once()
        mock_sleep.assert_not_called()

    def test_success_after_retries(self, mock_sleep: MagicMock) -> None:
        func = Mock(side_effect=[False, False, True])
        assert wait_for_condition(func, timeout=5.0, interval=0.5)
        assert func.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    def test_no_timeout(self, mock_sleep: MagicMock) -> None:
        func = Mock(return_value=False)
        assert not wait_for_condition(func, timeout=0, interval=0)
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("time.time")
    def test_timeout_reached(self, mock_time: MagicMock, mock_sleep: MagicMock) -> None:
        mock_time.side_effect = [0.0, 2.5, 5.0, 5.0, 5.0]
        func = Mock(return_value=False)
        assert not wait_for_condition(func, timeout=5.0, interval=1.0)
        assert func.call_count == 2
        assert mock_sleep.call_count == 1
