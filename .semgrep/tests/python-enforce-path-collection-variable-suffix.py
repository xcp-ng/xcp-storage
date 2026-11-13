from pathlib import Path, PurePath

# ------------------------------------------------------------------------------
# Declared as a collection of paths: variables.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-collection-variable-suffix
sockets: List[StrPath] = []
# ruleid: python-enforce-path-collection-variable-suffix
found: list[Path] = []
# ruleid: python-enforce-path-collection-variable-suffix
iterated: Iterator[Path]
# ruleid: python-enforce-path-collection-variable-suffix
prefixed: typing.List[Path] = []
# ok: python-enforce-path-collection-variable-suffix
unit_paths: List[Path] = []
# ok: python-enforce-path-collection-variable-suffix
prefixed_paths: Optional[typing.Sequence[StrPath]] = None
# ok: python-enforce-path-collection-variable-suffix
config: Optional[Path] = None
# ok: python-enforce-path-collection-variable-suffix
CONFIG: Final[Path] = Path("/a")
# ok: python-enforce-path-collection-variable-suffix
names: List[str] = []
# ok: python-enforce-path-collection-variable-suffix
mapping: Dict[str, Path] = {}

class Holder:
    def __init__(self) -> None:
        # ruleid: python-enforce-path-collection-variable-suffix
        self.units: List[Path] = []
        # ok: python-enforce-path-collection-variable-suffix
        self.unit_paths: List[Path] = []

# ------------------------------------------------------------------------------
# Declared as a collection of paths: parameters.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-collection-variable-suffix
def register(executables: Sequence[Path]) -> None:
    pass

# ruleid: python-enforce-path-collection-variable-suffix
def register_list(units: List[PurePath], dirs: Optional[Tuple[Path, ...]] = None) -> None:
    pass

# ok: python-enforce-path-collection-variable-suffix
def register_paths(executable_paths: Sequence[Path], paths: Iterable[PurePath]) -> None:
    pass

# ------------------------------------------------------------------------------
# Type wrappers.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-collection-variable-suffix
final_targets: Final[List[Path]] = []
# ruleid: python-enforce-path-collection-variable-suffix
final_names: Final[Tuple[StrPath, ...]] = ()
# ruleid: python-enforce-path-collection-variable-suffix
union_targets: Union[List[Path], None] = None
# ok: python-enforce-path-collection-variable-suffix
final_target_paths: Final[List[Path]] = []
# ok: python-enforce-path-collection-variable-suffix
union_target_paths: Union[List[Path], None] = None
