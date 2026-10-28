import unittest.mock
from unittest import mock
from unittest.mock import DEFAULT, PropertyMock, patch

# ------------------------------------------------------------------------------
# Patch of a target: `patch(...)`, as a decorator, a context manager or a call.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-mock-autospec
@patch("time.sleep")
def test_decorator() -> None:
    pass

def test_patch() -> None:
    # ruleid: python-enforce-mock-autospec
    with patch("module.function") as mock_function:
        pass
    # ruleid: python-enforce-mock-autospec
    with patch("module.function", side_effect=OSError) as mock_function:
        pass
    # ruleid: python-enforce-mock-autospec
    with open("x") as file, patch("module.function", return_value=1):
        pass
    # ruleid: python-enforce-mock-autospec
    patcher = patch("module.function")
    # ruleid: python-enforce-mock-autospec
    with patch("module.function", autospec=False) as mock_function:
        pass
    # ruleid: python-enforce-mock-autospec
    with patch("module.function", spec=True) as mock_function:
        pass
    # ok: python-enforce-mock-autospec
    with patch("module.function", autospec=True) as mock_function:
        pass
    # ok: python-enforce-mock-autospec
    with patch("module.function", side_effect=OSError, autospec=True) as mock_function:
        pass

# ------------------------------------------------------------------------------
# Patch of an attribute: `patch.object(...)`.
# ------------------------------------------------------------------------------

def test_patch_object(target: object) -> None:
    # ruleid: python-enforce-mock-autospec
    with patch.object(target, "method") as mock_method:
        pass
    # ruleid: python-enforce-mock-autospec
    with patch.object(target, "method", side_effect=OSError) as mock_method:
        pass
    # ruleid: python-enforce-mock-autospec
    with patch.object(target, "method", autospec=False) as mock_method:
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "method", autospec=True) as mock_method:
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "method", side_effect=OSError, autospec=True) as mock_method:
        pass

# ------------------------------------------------------------------------------
# Replaced by a value (positional `new` or `new=`): not a mock.
# ------------------------------------------------------------------------------

def test_value(target: object, tmp_path: object) -> None:
    # ok: python-enforce-mock-autospec
    with patch("module.DIR_PATH", tmp_path):
        pass
    # ok: python-enforce-mock-autospec
    with patch("module.DIR_PATH", new=tmp_path):
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "MAX_SIZE", 3):
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "MAX_SIZE", new=3):
        pass

# ------------------------------------------------------------------------------
# Patch of several attributes: `patch.multiple(...)`, mocks for the ones set to `DEFAULT`.
# ------------------------------------------------------------------------------

def test_patch_multiple() -> None:
    # ruleid: python-enforce-mock-autospec
    with patch.multiple("module", function=DEFAULT) as mock_functions:
        pass
    # ruleid: python-enforce-mock-autospec
    with patch.multiple("module", PORT=1, function=DEFAULT) as mock_functions:
        pass
    # ok: python-enforce-mock-autospec
    with patch.multiple("module", autospec=True, function=DEFAULT) as mock_functions:
        pass
    # ok: python-enforce-mock-autospec
    with patch.multiple("module", PORT=1, OTHER_PORT=2):
        pass

# ------------------------------------------------------------------------------
# Attribute created by the patch (`create=True`): nothing to check against.
# ------------------------------------------------------------------------------

def test_create(target: object) -> None:
    # ok: python-enforce-mock-autospec
    with patch("module.missing_function", create=True) as mock_missing_function:
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "missing_method", create=True) as mock_missing_method:
        pass

# ------------------------------------------------------------------------------
# Mock class chosen by the test (`new_callable=`).
# ------------------------------------------------------------------------------

def test_new_callable(target: object) -> None:
    # ok: python-enforce-mock-autospec
    with patch("module.Class.attribute", new_callable=PropertyMock) as mock_attribute:
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "attribute", new_callable=PropertyMock) as mock_attribute:
        pass

# ------------------------------------------------------------------------------
# Spy (`wraps=`): no `autospec`, Python 3.6 ignores `wraps=` with it.
# ------------------------------------------------------------------------------

def test_spy(target: object) -> None:
    # ok: python-enforce-mock-autospec
    with patch("module.function", wraps=print) as spy_function:
        pass
    # ok: python-enforce-mock-autospec
    with patch.object(target, "method", wraps=target.method) as spy_method:
        pass

# ------------------------------------------------------------------------------
# Prefixed forms: `unittest.mock.patch`, `mock.patch.object`, `mock.patch.multiple`.
# ------------------------------------------------------------------------------

def test_prefixed(target: object) -> None:
    # ruleid: python-enforce-mock-autospec
    with unittest.mock.patch("module.function") as mock_function:
        pass
    # ruleid: python-enforce-mock-autospec
    with mock.patch.object(target, "method") as mock_method:
        pass
    # ruleid: python-enforce-mock-autospec
    with mock.patch.multiple("module", function=mock.DEFAULT) as mock_functions:
        pass
    # ok: python-enforce-mock-autospec
    with unittest.mock.patch("module.function", autospec=True) as mock_function:
        pass
    # ok: python-enforce-mock-autospec
    with mock.patch.object(target, "method", autospec=True) as mock_method:
        pass
