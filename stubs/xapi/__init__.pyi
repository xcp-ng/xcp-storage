import argparse
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Sequence, Tuple, Union

def success(result: object) -> Dict[str, Any]: ...
def handle_exception(e: BaseException, code: object = None, params: object = None) -> NoReturn: ...

class XenAPIException(Exception):
    code: str
    params: List[Any]
    def __init__(self, code: str, params: List[Any]) -> None: ...

class MissingDependency(Exception):
    missing: object
    def __init__(self, missing: object) -> None: ...
    def __str__(self) -> str: ...

class Rpc_light_failure(Exception):
    name: str
    args: Tuple[Any, ...]
    def __init__(self, name: str, args: Iterable[Any]) -> None: ...
    def failure(self) -> Dict[str, Any]: ...

class Unimplemented(Rpc_light_failure):
    def __init__(self, name: str) -> None: ...

class InternalError(Rpc_light_failure):
    def __init__(self, error: str) -> None: ...

class UnmarshalException(InternalError):
    def __init__(self, thing: object, ty: object, desc: object) -> None: ...

class TypeError(InternalError):
    def __init__(self, expected: object, actual: object) -> None: ...

class UnknownMethod(InternalError):
    def __init__(self, name: object) -> None: ...

def is_long(x: object) -> bool: ...

class ListAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None
    ) -> None: ...
