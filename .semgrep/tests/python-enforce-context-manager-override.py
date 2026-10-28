import contextlib
import typing

import typing_extensions

from xcp_storage.typing import override

# ------------------------------------------------------------------------------
# Not decorated with `@override`.
# ------------------------------------------------------------------------------

class Bad:
    # ruleid: python-enforce-context-manager-override
    def __enter__(self) -> "Bad":
        return self

    @typing.final
    # ruleid: python-enforce-context-manager-override
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

# ------------------------------------------------------------------------------
# Imported decorator, also among other decorators.
# ------------------------------------------------------------------------------

class Imported(contextlib.AbstractContextManager):
    @override
    # ok: python-enforce-context-manager-override
    def __enter__(self) -> "Imported":
        return self

    @typing.final
    @override
    # ok: python-enforce-context-manager-override
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

# ------------------------------------------------------------------------------
# Prefixed decorator.
# ------------------------------------------------------------------------------

class Prefixed(contextlib.AbstractContextManager):
    @typing.override
    # ok: python-enforce-context-manager-override
    def __enter__(self) -> "Prefixed":
        return self

    @typing_extensions.override
    # ok: python-enforce-context-manager-override
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

# ------------------------------------------------------------------------------
# Other methods: not covered.
# ------------------------------------------------------------------------------

class Other:
    # ok: python-enforce-context-manager-override
    async def __aenter__(self) -> "Other":
        return self

    # ok: python-enforce-context-manager-override
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        pass

    # ok: python-enforce-context-manager-override
    def enter(self) -> "Other":
        return self
