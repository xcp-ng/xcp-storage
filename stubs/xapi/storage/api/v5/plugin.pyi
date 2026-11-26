import builtins
from typing import Any, Callable, Dict, List, Optional, Sequence, TypedDict, Union, type_check_only

from xapi import *

get_str = str
long = int
unicode = str
# Annotations use `builtins.str`: `str` is `bytes` in this module.
str = bytes

# ==============================================================================
# Types of the IDL (`plugin.ml`), for typing only.
# ==============================================================================

# Record `query_result`.
@type_check_only
class QueryResult(TypedDict):
    # Used in the XenAPI as `SR.type`.
    plugin: builtins.str
    name: builtins.str
    description: builtins.str
    vendor: builtins.str
    copyright: builtins.str
    version: builtins.str
    required_api_version: builtins.str
    features: List[builtins.str]
    # Description of each required `device_config` key.
    configuration: Dict[builtins.str, builtins.str]
    required_cluster_stack: List[builtins.str]

_Arguments = Dict[builtins.str, Any]

# ==============================================================================
# Plugin.
# ==============================================================================

# Checks the arguments and the result of the implementation.
class Plugin_server_dispatcher:
    _impl: Union[Plugin_skeleton, Plugin_test]
    _dispatcher_dict: Dict[builtins.str, Callable[[_Arguments], Any]]
    def __init__(self, impl: Union[Plugin_skeleton, Plugin_test]) -> None: ...
    def query(self, args: _Arguments) -> QueryResult: ...
    def ls(self, args: _Arguments) -> List[builtins.str]: ...
    def diagnostics(self, args: _Arguments) -> builtins.str: ...
    def _dispatch(self, method: builtins.str, params: Sequence[_Arguments]) -> Dict[builtins.str, Any]: ...

# Every method raises `Unimplemented`.
class Plugin_skeleton:
    def __init__(self) -> None: ...
    def query(self, dbg: builtins.str) -> QueryResult: ...
    # Returns the attached SRs.
    def ls(self, dbg: builtins.str) -> List[builtins.str]: ...
    def diagnostics(self, dbg: builtins.str) -> builtins.str: ...

# Returns placeholder values.
class Plugin_test:
    def __init__(self) -> None: ...
    def query(self, dbg: builtins.str) -> QueryResult: ...
    def ls(self, dbg: builtins.str) -> List[builtins.str]: ...
    def diagnostics(self, dbg: builtins.str) -> builtins.str: ...

# Parses the command line (or JSON from stdin with `--json`) and prints the JSON result.
class Plugin_commandline:
    impl: Union[Plugin_skeleton, Plugin_test]
    dispatcher: Plugin_server_dispatcher
    def __init__(self, impl: Union[Plugin_skeleton, Plugin_test]) -> None: ...
    def _parse_query(self) -> _Arguments: ...
    def _parse_ls(self) -> _Arguments: ...
    def _parse_diagnostics(self) -> _Arguments: ...
    def query(self) -> None: ...
    def ls(self) -> None: ...
    def diagnostics(self) -> None: ...

# ==============================================================================
# Demultiplexer of the `Plugin.*` methods.
# ==============================================================================

class plugin_server_dispatcher:
    Plugin: Plugin_server_dispatcher
    _dispatcher_dict: Dict[builtins.str, Callable[[builtins.str, Sequence[_Arguments]], Dict[builtins.str, Any]]]
    # `None` raises `AttributeError`.
    def __init__(self, Plugin: Optional[Plugin_server_dispatcher] = None) -> None: ...
    # Returns the JSON-RPC response: errors are returned, not raised.
    def _dispatch(self, method: builtins.str, params: Sequence[_Arguments]) -> Dict[builtins.str, Any]: ...

class plugin_server_test(plugin_server_dispatcher):
    def __init__(self) -> None: ...
