from unittest.mock import MagicMock, patch

import pytest

# ------------------------------------------------------------------------------
# Mock yielded by a fixture: `with patch(...) as x: yield x`.
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_fifo_lock_start_service() -> object:
    with patch("module.start_service", autospec=True) as mock_start_service:
        # ruleid: python-enforce-mock-fixture-name
        yield mock_start_service

@pytest.fixture(scope="module")
def run_command() -> object:
    with patch("module.run_command", autospec=True) as mock_run_command:
        # ruleid: python-enforce-mock-fixture-name
        yield mock_run_command

@pytest.fixture
def mock_run_command() -> object:
    with patch("module.run_command", autospec=True) as mock_run_command:
        # ok: python-enforce-mock-fixture-name
        yield mock_run_command

class TestClass:
    @pytest.fixture
    def mock_get_addresses(self) -> object:
        with open("x") as file, patch.object(object, "get_addresses", autospec=True) as mock_addresses:
            # ruleid: python-enforce-mock-fixture-name
            yield mock_addresses

    @pytest.fixture
    def mock_socketpair(self) -> object:
        with patch("socket.socketpair", autospec=True) as mock_socketpair:
            # ok: python-enforce-mock-fixture-name
            yield mock_socketpair

# ------------------------------------------------------------------------------
# Mock returned by a fixture: `x = MagicMock(); return x`.
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_ssl_sock() -> MagicMock:
    mock_sock = MagicMock()
    # ruleid: python-enforce-mock-fixture-name
    return mock_sock

@pytest.fixture
def mock_sock() -> MagicMock:
    mock_sock = MagicMock()
    # ok: python-enforce-mock-fixture-name
    return mock_sock

# ------------------------------------------------------------------------------
# Spy provided by a fixture: named `spy_` like its variable.
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_call(target: object) -> object:
    with patch.object(target, "_call", wraps=print) as spy_call:
        # ruleid: python-enforce-mock-fixture-name
        yield spy_call

@pytest.fixture
def spy_call(target: object) -> object:
    with patch.object(target, "_call", wraps=print) as spy_call:
        # ok: python-enforce-mock-fixture-name
        yield spy_call

# ------------------------------------------------------------------------------
# Not a mock (no `mock_`/`spy_` name), or not a fixture.
# ------------------------------------------------------------------------------

@pytest.fixture
def proc_fs(tmp_path: object) -> object:
    with patch("module.PROC_DIR_PATH", tmp_path):
        # ok: python-enforce-mock-fixture-name
        yield tmp_path

@pytest.fixture
def mock_listener_port() -> object:
    def impl() -> None:
        pass
    # ok: python-enforce-mock-fixture-name
    return impl

@pytest.fixture
def mock_sleep() -> object:
    with patch("module.time", autospec=True) as mock_time:
        # ok: python-enforce-mock-fixture-name
        yield mock_time.sleep

def create_mock() -> MagicMock:
    mock_sock = MagicMock()
    # ok: python-enforce-mock-fixture-name
    return mock_sock
