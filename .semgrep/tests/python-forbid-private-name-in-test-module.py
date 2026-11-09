# ------------------------------------------------------------------------------
# Assigned at module level: constant, type alias.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-private-name-in-test-module
_CONSTANT = 1
# ruleid: python-forbid-private-name-in-test-module
_CONSTANT: Final = 1
# ruleid: python-forbid-private-name-in-test-module
_SPEC = Spec(value=1)
# ruleid: python-forbid-private-name-in-test-module
_variable = 1
# ruleid: python-forbid-private-name-in-test-module
_Alias = Callable[..., int]
# ok: python-forbid-private-name-in-test-module
CONSTANT = 1
# ok: python-forbid-private-name-in-test-module
CONSTANT: Final = 1
# ok: python-forbid-private-name-in-test-module
__test__ = False
# ok: python-forbid-private-name-in-test-module
_DRBD_MODULE = Drbd.__module__
# ok: python-forbid-private-name-in-test-module
_DRBD_MODULE: Final = Drbd.__module__

def test_function() -> None:
    # ok: python-forbid-private-name-in-test-module
    _LOCAL = 1

class TestClass:
    # ok: python-forbid-private-name-in-test-module
    _ATTRIBUTE = 1

# ------------------------------------------------------------------------------
# Defined function.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-private-name-in-test-module
def _helper() -> None:
    pass
# ruleid: python-forbid-private-name-in-test-module
async def _async_helper() -> None:
    pass
@pytest.fixture
# ruleid: python-forbid-private-name-in-test-module
def _fixture() -> int:
    return 1
# ok: python-forbid-private-name-in-test-module
def helper() -> None:
    pass
# ok: python-forbid-private-name-in-test-module
def test_function() -> None:
    pass

def factory():
    # ok: python-forbid-private-name-in-test-module
    def _create():
        pass
    with context():
        # ok: python-forbid-private-name-in-test-module
        def _deep_create():
            pass
    return _create

class TestMethods:
    # ok: python-forbid-private-name-in-test-module
    def _method(self) -> None:
        if condition:
            # ok: python-forbid-private-name-in-test-module
            def _deep_function() -> None:
                pass

# ------------------------------------------------------------------------------
# Defined class.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-private-name-in-test-module
class _Fake:
    pass
# ruleid: python-forbid-private-name-in-test-module
class _Spec(NamedTuple):
    value: int
# ok: python-forbid-private-name-in-test-module
class Fake:
    pass

def helper() -> None:
    for item in items:
        # ok: python-forbid-private-name-in-test-module
        class _LocalClass:
            pass

class Outer:
    # ok: python-forbid-private-name-in-test-module
    class _Inner:
        pass
