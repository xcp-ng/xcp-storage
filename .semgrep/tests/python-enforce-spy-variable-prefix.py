import unittest.mock
from unittest import mock
from unittest.mock import MagicMock, Mock, patch

# ------------------------------------------------------------------------------
# Spy of a target: `with patch(..., wraps=...) as x`, at any position of a multi-item `with`.
# ------------------------------------------------------------------------------

def test_patch(target: object) -> None:
    # ruleid: python-enforce-spy-variable-prefix
    with patch("module.function", wraps=target.method) as function:
        pass
    # ruleid: python-enforce-spy-variable-prefix
    with patch("module.function", wraps=target.method) as spy:
        pass
    # ruleid: python-enforce-spy-variable-prefix
    with open("x") as file, patch("module.function", autospec=True, wraps=target.method) as function_spy:
        pass
    # ok: python-enforce-spy-variable-prefix
    with patch("module.function", wraps=target.method) as spy_function:
        pass
    # ok: python-enforce-spy-variable-prefix
    with patch("module.function", wraps=target.method):
        pass

# ------------------------------------------------------------------------------
# Spy of an attribute: `with patch.object(..., wraps=...) as x`.
# ------------------------------------------------------------------------------

def test_patch_object(target: object) -> None:
    # ruleid: python-enforce-spy-variable-prefix
    with patch.object(target, "method", wraps=target.method) as call_spy:
        pass
    # ruleid: python-enforce-spy-variable-prefix
    with patch("module.function") as mock_function, patch.object(target, "method", wraps=target.method) as method:
        pass
    # ok: python-enforce-spy-variable-prefix
    with patch.object(target, "method", wraps=target.method) as spy_method:
        pass

# ------------------------------------------------------------------------------
# Spy started by hand (`patch(...).start()`) or entered in an `ExitStack`.
# ------------------------------------------------------------------------------

def test_started_patch(target: object, stack: object) -> None:
    # ruleid: python-enforce-spy-variable-prefix
    function = patch("module.function", wraps=target.method).start()
    # ruleid: python-enforce-spy-variable-prefix
    method = patch.object(target, "method", wraps=target.method).start()
    # ruleid: python-enforce-spy-variable-prefix
    function = stack.enter_context(patch("module.function", wraps=target.method))
    # ruleid: python-enforce-spy-variable-prefix
    method = stack.enter_context(patch.object(target, "method", wraps=target.method))
    # ok: python-enforce-spy-variable-prefix
    spy_function = patch("module.function", wraps=target.method).start()
    # ok: python-enforce-spy-variable-prefix
    spy_method = stack.enter_context(patch.object(target, "method", wraps=target.method))

# ------------------------------------------------------------------------------
# Spy created directly: `Mock(wraps=...)`, `MagicMock(wraps=...)`, `AsyncMock`, `create_autospec`...
# ------------------------------------------------------------------------------

def test_direct_spy(target: object) -> None:
    # ruleid: python-enforce-spy-variable-prefix
    function = Mock(wraps=print)
    # ruleid: python-enforce-spy-variable-prefix
    method = MagicMock(wraps=target.method)
    # ruleid: python-enforce-spy-variable-prefix
    coroutine = unittest.mock.AsyncMock(wraps=target.method)
    # ruleid: python-enforce-spy-variable-prefix
    function = unittest.mock.create_autospec(print, wraps=print)
    # ok: python-enforce-spy-variable-prefix
    spy_function = Mock(wraps=print)
    # ok: python-enforce-spy-variable-prefix
    patcher = patch("module.function", wraps=print)

# ------------------------------------------------------------------------------
# Mock (no `wraps=`): checked by `python-enforce-mock-variable-prefix`.
# ------------------------------------------------------------------------------

def test_mock(target: object) -> None:
    # ok: python-enforce-spy-variable-prefix
    with patch("module.function") as function:
        pass
    # ok: python-enforce-spy-variable-prefix
    with patch.object(target, "method", side_effect=OSError) as method:
        pass
    # ok: python-enforce-spy-variable-prefix
    function = patch("module.function").start()
    # ok: python-enforce-spy-variable-prefix
    function = Mock(return_value=True)

# ------------------------------------------------------------------------------
# Prefixed forms: `unittest.mock.patch`, `mock.patch`, `unittest.mock.MagicMock`.
# ------------------------------------------------------------------------------

def test_prefixed_forms(target: object) -> None:
    # ruleid: python-enforce-spy-variable-prefix
    with unittest.mock.patch.object(target, "method", wraps=target.method) as method:
        pass
    # ruleid: python-enforce-spy-variable-prefix
    with mock.patch("module.function", wraps=target.method) as function:
        pass
    # ruleid: python-enforce-spy-variable-prefix
    method = unittest.mock.MagicMock(wraps=target.method)
    # ok: python-enforce-spy-variable-prefix
    with mock.patch.object(target, "method", wraps=target.method) as spy_method:
        pass
