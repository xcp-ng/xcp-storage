import builtins
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    NotRequired,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
    type_check_only,
)

from xapi import *
from xapi.storage.api.v5.volume import Volume

get_str = str
long = int
unicode = str
# Annotations use `builtins.str`: `str` is `bytes` in this module.
str = bytes

# ==============================================================================
# Types of the IDL (`task.ml`), for typing only.
# ==============================================================================

# Variant `async_result_t`: `("UnitResult",)` or `("Volume", volume)`.
AsyncResult = Union[Tuple[Literal["UnitResult"]], Tuple[Literal["Volume"], Volume]]

# Record `completion_t`.
@type_check_only
class Completion(TypedDict):
    duration: float
    result: NotRequired[AsyncResult]

# Variant `state`: `("Pending", progress from 0 to 1)`, `("Completed", completion)` or `("Failed", error)`.
# Not a union of tuples: mypy cannot infer a tuple literal against it.
TaskState = Tuple[Literal["Pending", "Completed", "Failed"], Union[float, Completion, builtins.str]]

# Record `task`.
@type_check_only
class Task(TypedDict):
    id: builtins.str
    debug_info: builtins.str
    ctime: float
    state: TaskState

_Arguments = Dict[builtins.str, Any]

# ==============================================================================
# Task.
# ==============================================================================

# Checks the arguments and the result of the implementation.
class Task_server_dispatcher:
    _impl: Union[Task_skeleton, Task_test]
    _dispatcher_dict: Dict[builtins.str, Callable[[_Arguments], Any]]
    def __init__(self, impl: Union[Task_skeleton, Task_test]) -> None: ...
    def stat(self, args: _Arguments) -> Task: ...
    def cancel(self, args: _Arguments) -> None: ...
    def destroy(self, args: _Arguments) -> None: ...
    def ls(self, args: _Arguments) -> List[builtins.str]: ...
    def _dispatch(self, method: builtins.str, params: Sequence[_Arguments]) -> Dict[builtins.str, Any]: ...

# Every method raises `Unimplemented`.
class Task_skeleton:
    def __init__(self) -> None: ...
    def stat(self, dbg: builtins.str, id: builtins.str) -> Task: ...
    def cancel(self, dbg: builtins.str, id: builtins.str) -> None: ...
    def destroy(self, dbg: builtins.str, id: builtins.str) -> None: ...
    def ls(self, dbg: builtins.str) -> List[builtins.str]: ...

# Returns placeholder values, not always valid (`None` for a variant...).
class Task_test:
    def __init__(self) -> None: ...
    def stat(self, dbg: builtins.str, id: builtins.str) -> Task: ...
    def cancel(self, dbg: builtins.str, id: builtins.str) -> None: ...
    def destroy(self, dbg: builtins.str, id: builtins.str) -> None: ...
    def ls(self, dbg: builtins.str) -> List[builtins.str]: ...

# Parses the command line (or JSON from stdin with `--json`) and prints the JSON result.
class Task_commandline:
    impl: Union[Task_skeleton, Task_test]
    dispatcher: Task_server_dispatcher
    def __init__(self, impl: Union[Task_skeleton, Task_test]) -> None: ...
    def _parse_stat(self) -> _Arguments: ...
    def _parse_cancel(self) -> _Arguments: ...
    def _parse_destroy(self) -> _Arguments: ...
    def _parse_ls(self) -> _Arguments: ...
    def stat(self) -> None: ...
    def cancel(self) -> None: ...
    def destroy(self) -> None: ...
    def ls(self) -> None: ...

# ==============================================================================
# Demultiplexer of the `Task.*` methods.
# ==============================================================================

class task_server_dispatcher:
    Task: Task_server_dispatcher
    _dispatcher_dict: Dict[builtins.str, Callable[[builtins.str, Sequence[_Arguments]], Dict[builtins.str, Any]]]
    # `None` raises `AttributeError`.
    def __init__(self, Task: Optional[Task_server_dispatcher] = None) -> None: ...
    # Returns the JSON-RPC response: errors are returned, not raised.
    def _dispatch(self, method: builtins.str, params: Sequence[_Arguments]) -> Dict[builtins.str, Any]: ...

class task_server_test(task_server_dispatcher):
    def __init__(self) -> None: ...
