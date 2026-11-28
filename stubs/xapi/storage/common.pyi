from typing import Literal, Sequence, Tuple, Union, overload

from xapi.storage import log as log

@overload
def call(
    dbg: str,
    cmd_args: Sequence[str],
    error: bool = True,
    simple: Literal[True] = True,
    expRc: int = 0
) -> bytes: ...

@overload
def call(
    dbg: str,
    cmd_args: Sequence[str],
    error: bool,
    simple: Literal[False],
    expRc: int = 0
) -> Tuple[bytes, bytes, int]: ...

@overload
def call(
    dbg: str,
    cmd_args: Sequence[str],
    error: bool = True,
    *,
    simple: Literal[False],
    expRc: int = 0
) -> Tuple[bytes, bytes, int]: ...

@overload
def call(
    dbg: str,
    cmd_args: Sequence[str],
    error: bool = True,
    simple: bool = True,
    expRc: int = 0
) -> Union[bytes, Tuple[bytes, bytes, int]]: ...
