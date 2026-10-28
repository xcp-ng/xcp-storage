# ------------------------------------------------------------------------------
# Variables: assigned or declared.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-function-abbreviation
func = get()
# ruleid: python-forbid-function-abbreviation
callback_fn: Callable
# ruleid: python-forbid-function-abbreviation
async_func: Callable = get()
# ok: python-forbid-function-abbreviation
function = get()
# ok: python-forbid-function-abbreviation
functions: List[Callable] = []

class Holder:
    def __init__(self) -> None:
        # ruleid: python-forbid-function-abbreviation
        self.func = None
        # ruleid: python-forbid-function-abbreviation
        self.typed_func: Optional[Callable] = None

# ------------------------------------------------------------------------------
# Name parts: a whole word between underscores, not a prefix of a longer word.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-function-abbreviation
fun_fact = get()
# ok: python-forbid-function-abbreviation
funnel = get()

# ------------------------------------------------------------------------------
# Functions and classes.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-function-abbreviation
def run_func() -> None:
    pass

# ruleid: python-forbid-function-abbreviation
class FuncHolder:
    pass

# ok: python-forbid-function-abbreviation
def functional(function: Callable) -> None:
    pass

# ------------------------------------------------------------------------------
# Parameters.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-function-abbreviation
def call(fn: Callable) -> None:
    pass

# ------------------------------------------------------------------------------
# `*args`, `**kwargs`, `for` and `with` targets.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-function-abbreviation
def call_all(*funcs, **fns) -> None:
    # ruleid: python-forbid-function-abbreviation
    for fun in funcs:
        pass
    # ruleid: python-forbid-function-abbreviation
    with get() as funcs_list:
        pass
