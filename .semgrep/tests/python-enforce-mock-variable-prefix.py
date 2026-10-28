import unittest.mock
from unittest import mock
from unittest.mock import MagicMock, Mock, create_autospec, patch

# ------------------------------------------------------------------------------
# Patch of a target: `with patch(...) as x`, at any position of a multi-item `with`.
# ------------------------------------------------------------------------------

def test_patch() -> None:
    # ruleid: python-enforce-mock-variable-prefix
    with patch("module.function") as function:
        pass
    # ruleid: python-enforce-mock-variable-prefix
    with patch("module.function") as mock:
        pass
    # ruleid: python-enforce-mock-variable-prefix
    with open("x") as file, patch("module.function") as patched_function:
        pass
    # ruleid: python-enforce-mock-variable-prefix
    with patch("module.function", autospec=True) as function_mock, open("x") as file:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch("module.function") as mock_function:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch("module.function", autospec=True) as mock_function, open("x") as file:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch("module.function"):
        pass

# ------------------------------------------------------------------------------
# Patch of an attribute: `with patch.object(...) as x`.
# ------------------------------------------------------------------------------

def test_patch_object(target: object) -> None:
    # ruleid: python-enforce-mock-variable-prefix
    with patch.object(target, "method") as method:
        pass
    # ruleid: python-enforce-mock-variable-prefix
    with patch.object(target, "method", side_effect=OSError) as mock:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch.object(target, "method") as mock_method:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch.object(target, "method"):
        pass

# ------------------------------------------------------------------------------
# Patch started by hand (`patch(...).start()`) or entered in an `ExitStack`.
# ------------------------------------------------------------------------------

def test_started_patch(target: object, stack: object) -> None:
    # ruleid: python-enforce-mock-variable-prefix
    function = patch("module.function").start()
    # ruleid: python-enforce-mock-variable-prefix
    method = patch.object(target, "method").start()
    # ruleid: python-enforce-mock-variable-prefix
    function = stack.enter_context(patch("module.function"))
    # ruleid: python-enforce-mock-variable-prefix
    method = stack.enter_context(patch.object(target, "method"))
    # ok: python-enforce-mock-variable-prefix
    mock_function = patch("module.function").start()
    # ok: python-enforce-mock-variable-prefix
    mock_method = stack.enter_context(patch.object(target, "method"))
    # ok: python-enforce-mock-variable-prefix
    patcher = patch("module.function")

# ------------------------------------------------------------------------------
# Mock created directly: `Mock`, `MagicMock`, `NonCallableMagicMock`, `AsyncMock`, `create_autospec`.
# ------------------------------------------------------------------------------

def test_direct_mock() -> None:
    # ruleid: python-enforce-mock-variable-prefix
    function = Mock(return_value=True)
    # ruleid: python-enforce-mock-variable-prefix
    sock = MagicMock(spec=object)
    # ruleid: python-enforce-mock-variable-prefix
    sock = unittest.mock.NonCallableMagicMock()
    # ruleid: python-enforce-mock-variable-prefix
    coroutine = unittest.mock.AsyncMock()
    # ruleid: python-enforce-mock-variable-prefix
    function = create_autospec(print)
    # ruleid: python-enforce-mock-variable-prefix
    sock: MagicMock = MagicMock()
    # ok: python-enforce-mock-variable-prefix
    mock_sock = MagicMock()
    # ok: python-enforce-mock-variable-prefix
    result = print(MagicMock())

def test_tuple_assignment() -> None:
    # Each name of a tuple assignment is checked.
    # ruleid: python-enforce-mock-variable-prefix
    first, second = MagicMock(), MagicMock()
    # ok: python-enforce-mock-variable-prefix
    mock_first, mock_second = MagicMock(), MagicMock()

# ------------------------------------------------------------------------------
# Spy (`wraps=`): checked by `python-enforce-spy-variable-prefix`.
# ------------------------------------------------------------------------------

def test_spy(target: object) -> None:
    # ruleid: python-enforce-mock-variable-prefix
    with patch.object(target, "method", wraps=target.method) as spy_method, patch("module.function") as function:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch("module.function", wraps=target.method) as function_spy:
        pass
    # ok: python-enforce-mock-variable-prefix
    with patch.object(target, "method", wraps=target.method) as method_spy:
        pass
    # ok: python-enforce-mock-variable-prefix
    method_spy = patch.object(target, "method", wraps=target.method).start()
    # ok: python-enforce-mock-variable-prefix
    function_spy = Mock(wraps=print)
    # ok: python-enforce-mock-variable-prefix
    with patch.object(target, "method", wraps=target.method) as method_spy, patch("module.function") as mock_function:
        pass

# ------------------------------------------------------------------------------
# Prefixed forms: `unittest.mock.patch`, `mock.patch`, `mock.MagicMock`.
# ------------------------------------------------------------------------------

def test_prefixed_forms(target: object) -> None:
    # ruleid: python-enforce-mock-variable-prefix
    with unittest.mock.patch("module.function") as function:
        pass
    # ruleid: python-enforce-mock-variable-prefix
    with mock.patch.object(target, "method") as method:
        pass
    # ruleid: python-enforce-mock-variable-prefix
    sock = mock.MagicMock()
    # ok: python-enforce-mock-variable-prefix
    with unittest.mock.patch.object(target, "method") as mock_method:
        pass
    # ok: python-enforce-mock-variable-prefix
    with mock.patch("module.function", wraps=target.method) as function_spy:
        pass
