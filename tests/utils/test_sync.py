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

from unittest.mock import MagicMock, Mock

import pytest

from tests.utils.exception import raises_exactly
from tests.utils.time import SimulatedTime
from xcp_storage.utils.sync import wait_for_condition, wait_for_stable_value

# ==============================================================================

class TestWaitForCondition:
    def test_success(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(return_value=True)
        assert wait_for_condition(mock_function, timeout=5.0, interval=0.1)
        mock_function.assert_called_once()
        mock_sleep.assert_not_called()

    def test_success_after_retries(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(side_effect=[False, False, True])
        assert wait_for_condition(mock_function, timeout=5.0, interval=0.5)
        assert mock_function.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    def test_no_timeout(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(return_value=False)
        assert not wait_for_condition(mock_function, timeout=0, interval=0)
        mock_function.assert_called_once()
        mock_sleep.assert_not_called()

    def test_negative_timeout(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(return_value=False)
        assert not wait_for_condition(mock_function, timeout=-1.0, interval=1.0)
        mock_function.assert_called_once()
        mock_sleep.assert_not_called()

    def test_timeout_reached(self, simulated_time: SimulatedTime, mock_sleep: MagicMock) -> None:
        def condition() -> bool:
            # Calls at 0 and 3.5 s, each one lasting 2.5 s.
            simulated_time.advance(2.5)
            return False

        mock_function = Mock(side_effect=condition)
        assert not wait_for_condition(mock_function, timeout=5.0, interval=1.0)
        assert mock_function.call_count == 2
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(1.0)

    def test_sleep_is_capped_by_remaining_time(self, simulated_time: SimulatedTime, mock_sleep: MagicMock) -> None:
        def condition() -> bool:
            # The first call lasts 4.5 s: 0.5 s left.
            simulated_time.advance(4.5)
            return False

        assert not wait_for_condition(condition, timeout=5.0, interval=10.0)
        mock_sleep.assert_called_once_with(0.5)

    def test_exception_is_propagated(self, mock_sleep: MagicMock) -> None:
        exception_message = "Explosion!"
        mock_function = Mock(side_effect=Exception(exception_message))
        with raises_exactly(Exception, exception_message):
            wait_for_condition(mock_function, timeout=5.0, interval=1.0)
        mock_sleep.assert_not_called()

# ------------------------------------------------------------------------------

class TestWaitForStableValue:
    def test_trivial_stable(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(return_value=1)
        assert wait_for_stable_value(mock_function, timeout=5.0, interval=0.1) == (True, 1)
        assert mock_function.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    def test_trivial_with_single_stable_value(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(return_value=1)
        assert wait_for_stable_value(mock_function, timeout=5.0, interval=0.1, stable_count=1) == (True, 1)
        mock_function.assert_called_once()
        mock_sleep.assert_not_called()

    def test_no_timeout_with_stable_count_greater_than_one(self, mock_sleep: MagicMock) -> None:
        # False result because function is called only once and default stable count is 2.
        mock_function = Mock(return_value=1)
        assert wait_for_stable_value(mock_function, timeout=0, interval=0) == (False, 1)
        mock_function.assert_called_once()
        mock_sleep.assert_not_called()

    @pytest.mark.usefixtures("simulated_time")
    def test_timeout_reached(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(side_effect=[1, 2, 3, 4])
        assert wait_for_stable_value(mock_function, timeout=5.0, interval=2.0) == (False, 4)
        assert mock_function.call_count == 4
        assert [delay for (delay, ), _ in mock_sleep.call_args_list] == [2.0, 2.0, 1.0]

    def test_stable_after_changes(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(side_effect=[1, 2, 3, 3])
        assert wait_for_stable_value(mock_function, timeout=5.0, interval=0.5) == (True, 3)
        assert mock_function.call_count == 4
        assert mock_sleep.call_count == 3
        mock_sleep.assert_called_with(0.5)

    def test_change_restarts_stable_count(self, mock_sleep: MagicMock) -> None:
        mock_function = Mock(side_effect=[1, 1, 2, 2, 2])
        assert wait_for_stable_value(mock_function, timeout=5.0, interval=0.5, stable_count=3) == (True, 2)
        assert mock_function.call_count == 5
        assert mock_sleep.call_count == 4

    @pytest.mark.usefixtures("simulated_time")
    def test_change_restarts_stable_duration(self) -> None:
        mock_function = Mock(side_effect=[1, 1, 2, 2, 2, 2])
        assert wait_for_stable_value(mock_function, timeout=10.0, interval=1.0, stable_duration=2.5) == (True, 2)
        assert mock_function.call_count == 6

    @pytest.mark.usefixtures("simulated_time")
    def test_both_criteria_are_required(self) -> None:
        # The stable duration is reached at the second call, the stable count only at the third one.
        mock_function = Mock(return_value=1)
        assert wait_for_stable_value(
            mock_function, timeout=10.0, interval=1.0, stable_count=3, stable_duration=0.5
        ) == (True, 1)
        assert mock_function.call_count == 3

    @pytest.mark.parametrize("stable_count", [0, -1])
    def test_invalid_stable_count(self, mock_sleep: MagicMock, stable_count: int) -> None:
        mock_function = Mock(return_value=1)
        with raises_exactly(ValueError, f"Invalid stable count: `{stable_count}`."):
            wait_for_stable_value(mock_function, timeout=5.0, interval=1.0, stable_count=stable_count)
        mock_function.assert_not_called()
        mock_sleep.assert_not_called()

    def test_exception_is_propagated(self, mock_sleep: MagicMock) -> None:
        exception_message = "Explosion!"
        mock_function = Mock(side_effect=[1, Exception(exception_message)])
        with raises_exactly(Exception, exception_message):
            wait_for_stable_value(mock_function, timeout=5.0, interval=1.0)
        mock_sleep.assert_called_once_with(1.0)
