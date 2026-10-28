from functools import wraps

# ------------------------------------------------------------------------------
# Wrapper returned by a decorator, calling the decorated function.
# ------------------------------------------------------------------------------

def untyped(function):
    # ruleid: python-enforce-wraps-on-wrapper
    def wrapper(*args, **kwargs):
        result = function(*args, **kwargs)
        return result
    return wrapper

def asynchronous(function):
    # ruleid: python-enforce-wraps-on-wrapper
    async def wrapper(*args, **kwargs):
        return await function(*args, **kwargs)
    return wrapper

class Decorators:
    def method(self, function: Callable) -> Callable:
        # ruleid: python-enforce-wraps-on-wrapper
        def wrapper(self_, *args, **kwargs) -> None:
            function(self_, *args, **kwargs)
        return wrapper

def not_a_decorator(function):
    # ok: python-enforce-wraps-on-wrapper
    def helper(*args, **kwargs):
        return function(*args, **kwargs)
    return helper(1)

def returns_function(function):
    # ok: python-enforce-wraps-on-wrapper
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)
    return function

def other_call(function):
    # ok: python-enforce-wraps-on-wrapper
    def wrapper(*args, **kwargs):
        return other(*args, **kwargs)
    return wrapper

def positional_only(function):
    # ok: python-enforce-wraps-on-wrapper
    def wrapper(*args):
        return function(*args)
    return wrapper

def callback(function, *args, **kwargs):
    # ok: python-enforce-wraps-on-wrapper
    def on_exit(exc_type, exc, traceback):
        function(*args, **kwargs)
    return on_exit

# ------------------------------------------------------------------------------
# Annotated parameters: matched by the unannotated pattern parameters.
# ------------------------------------------------------------------------------

def typed(function: Callable[..., int]) -> Callable[..., int]:
    # ruleid: python-enforce-wraps-on-wrapper
    def wrapper(*args: Any, **kwargs: Any) -> int:
        return function(*args, **kwargs)
    return wrapper

def typed_function(function: Callable[..., int]):
    # ruleid: python-enforce-wraps-on-wrapper
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)
    return wrapper

def typed_arguments(function):
    # ruleid: python-enforce-wraps-on-wrapper
    def wrapper(*args: Any, **kwargs: Any) -> int:
        return function(*args, **kwargs)
    return wrapper

# ------------------------------------------------------------------------------
# Decorated with `wraps`: imported (`from functools import wraps`) or prefixed.
# ------------------------------------------------------------------------------

def decorated(function):
    @wraps(function)
    # ok: python-enforce-wraps-on-wrapper
    def wrapper(*args: Any, **kwargs: Any) -> int:
        return function(*args, **kwargs)
    return wrapper

def prefixed(function):
    @functools.wraps(function)
    # ok: python-enforce-wraps-on-wrapper
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)
    return wrapper
