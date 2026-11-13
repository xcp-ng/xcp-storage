# ------------------------------------------------------------------------------
# Assigned an exception: `x = Exception(...)`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exception-variable-suffix
failure = Exception("x")
# ok: python-enforce-exception-variable-suffix
exception = Exception("x")

class Holder:
    def __init__(self) -> None:
        # ruleid: python-enforce-exception-variable-suffix
        self.last = Exception()

# ------------------------------------------------------------------------------
# Declared as an exception: `x: Optional[Exception]`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exception-variable-suffix
cause: BaseException
# ruleid: python-enforce-exception-variable-suffix
last: Optional[JsonRpcException] = None

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-exception-variable-suffix
        self.cause: Optional[Exception] = None
        # ok: python-enforce-exception-variable-suffix
        self.cause_exception: Optional[Exception] = None

# ruleid: python-enforce-exception-variable-suffix
def handle(cause: Exception) -> None:
    pass

# ok: python-enforce-exception-variable-suffix
def handle_ok(exception: Exception, base_exception: Optional[BaseException] = None) -> None:
    pass

# ------------------------------------------------------------------------------
# Type wrappers.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exception-variable-suffix
final_cause: Final[Exception] = Exception()
# ruleid: python-enforce-exception-variable-suffix
typed_cause: Exception = Exception()
