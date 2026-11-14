import pytest

# ------------------------------------------------------------------------------
# Assigned at module level: constant, type alias.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-conftest-private-names
CONSTANT = 1
# ruleid: python-enforce-conftest-private-names
CONSTANT: Final = 1
# ruleid: python-enforce-conftest-private-names
Alias = Callable[..., int]
# ruleid: python-enforce-conftest-private-names
variable = 1
# ok: python-enforce-conftest-private-names
_CONSTANT = 1
# ok: python-enforce-conftest-private-names
_CONSTANT: Final = 1
# ok: python-enforce-conftest-private-names
_Alias = Callable[..., int]
# ok: python-enforce-conftest-private-names
pytest_plugins = ["plugin"]

def _function() -> None:
    # ok: python-enforce-conftest-private-names
    local = 1

class _Class:
    # ok: python-enforce-conftest-private-names
    ATTRIBUTE = 1

# ------------------------------------------------------------------------------
# Defined function, not a fixture.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-conftest-private-names
def helper() -> None:
    pass
# ruleid: python-enforce-conftest-private-names
async def async_helper() -> None:
    pass
@other_decorator
# ruleid: python-enforce-conftest-private-names
def decorated_helper() -> None:
    pass
# ok: python-enforce-conftest-private-names
def _helper() -> None:
    pass
# ok: python-enforce-conftest-private-names
def pytest_addoption(parser):
    pass
# ok: python-enforce-conftest-private-names
@pytest.fixture
def fixture() -> int:
    return 1
# ok: python-enforce-conftest-private-names
@pytest.fixture(scope="session")
def session_fixture() -> int:
    return 1
# ok: python-enforce-conftest-private-names
@pytest.fixture
async def async_fixture() -> int:
    return 1

@pytest.fixture
def factory_fixture():
    # ok: python-enforce-conftest-private-names
    def create():
        pass
    with context():
        # ok: python-enforce-conftest-private-names
        def deep_create():
            pass
    return create

class _Helper:
    # ok: python-enforce-conftest-private-names
    def method(self) -> None:
        if condition:
            # ok: python-enforce-conftest-private-names
            def deep_function() -> None:
                pass

# ------------------------------------------------------------------------------
# Defined class.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-conftest-private-names
class Helper:
    pass
# ruleid: python-enforce-conftest-private-names
class Spec(NamedTuple):
    value: int
# ok: python-enforce-conftest-private-names
class _Helper:
    pass

def _function() -> None:
    for item in items:
        # ok: python-enforce-conftest-private-names
        class LocalClass:
            pass

class _Outer:
    # ok: python-enforce-conftest-private-names
    class Inner:
        pass
