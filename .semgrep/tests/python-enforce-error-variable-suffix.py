# ------------------------------------------------------------------------------
# Assigned an error: `x = OSError(...)`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-error-variable-suffix
failure = ValueError("x")
# ruleid: python-enforce-error-variable-suffix
failure2 = errors.LockError("x")
# ok: python-enforce-error-variable-suffix
error = ValueError("x")
# ok: python-enforce-error-variable-suffix
LAST_ERROR: Final = ValueError("x")
# ok: python-enforce-error-variable-suffix
errors_count = count_errors()

class Holder:
    def __init__(self) -> None:
        # ruleid: python-enforce-error-variable-suffix
        self.last = OSError()
        # ok: python-enforce-error-variable-suffix
        self.last_error = OSError()

# ------------------------------------------------------------------------------
# Declared as an error: `x: Optional[OSError]`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-error-variable-suffix
cause: OSError
# ruleid: python-enforce-error-variable-suffix
last: Optional[SocketError] = None

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-error-variable-suffix
        self.cause: Optional[OSError] = None
        # ok: python-enforce-error-variable-suffix
        self.cause_error: Optional[OSError] = None

# ruleid: python-enforce-error-variable-suffix
def handle(cause: OSError) -> None:
    pass

# ok: python-enforce-error-variable-suffix
def handle_ok(error: OSError, socket_error: Optional[SocketError] = None) -> None:
    pass

# ------------------------------------------------------------------------------
# Type wrappers.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-error-variable-suffix
final_cause: Final[OSError] = OSError()
# ruleid: python-enforce-error-variable-suffix
mixed: Union[str, OSError] = ""
# ruleid: python-enforce-error-variable-suffix
union_cause: Union[OSError, None] = None
# ruleid: python-enforce-error-variable-suffix
other: OSError | None = None
# ok: python-enforce-error-variable-suffix
union_error: Union[OSError, None] = None
# ok: python-enforce-error-variable-suffix
not_error: Union[OSErrorish, None] = None
