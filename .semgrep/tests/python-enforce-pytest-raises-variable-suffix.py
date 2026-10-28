import pytest

import tests.utils.exception
from tests.utils.exception import raises_exactly

# ------------------------------------------------------------------------------
# `with pytest.raises(...) as x`, at any position of a multi-item `with`.
# ------------------------------------------------------------------------------

def test_names() -> None:
    # ruleid: python-enforce-pytest-raises-variable-suffix
    with pytest.raises(ValueError) as error:
        pass
    # ruleid: python-enforce-pytest-raises-variable-suffix
    with open("x") as file, pytest.raises(ValueError) as caught:
        pass
    # ruleid: python-enforce-pytest-raises-variable-suffix
    with pytest.raises(ValueError) as info, open("x") as file:
        pass
    with pytest.raises(
        ValueError,
    # ruleid: python-enforce-pytest-raises-variable-suffix
    ) as split:
        pass
    # ok: python-enforce-pytest-raises-variable-suffix
    with pytest.raises(ValueError) as exc_info:
        pass
    # ok: python-enforce-pytest-raises-variable-suffix
    with patch("x"), pytest.raises(ValueError) as lock_exc_info:
        pass
    # ok: python-enforce-pytest-raises-variable-suffix
    with pytest.raises(ValueError):
        pass

# ------------------------------------------------------------------------------
# `with raises_exactly(...) as x`: project helper yielding the info of its `pytest.raises`.
# ------------------------------------------------------------------------------

def test_raises_exactly_names() -> None:
    # ruleid: python-enforce-pytest-raises-variable-suffix
    with raises_exactly(ValueError, "Failure.") as error_info:
        pass
    # ruleid: python-enforce-pytest-raises-variable-suffix
    with tests.utils.exception.raises_exactly(ValueError, "Failure.") as info:
        pass
    # ok: python-enforce-pytest-raises-variable-suffix
    with raises_exactly(ValueError, "Failure.") as exc_info:
        pass
    # ok: python-enforce-pytest-raises-variable-suffix
    with raises_exactly(ValueError, "Failure."):
        pass
    # ok: python-enforce-pytest-raises-variable-suffix
    with other.raises_exactly(ValueError, "Failure.") as result:
        pass
