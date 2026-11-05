# ------------------------------------------------------------------------------
# `__exit__` and `__aexit__` signatures.
# ------------------------------------------------------------------------------

class Bad:
    # ruleid: python-enforce-context-manager-exit-signature
    def __exit__(self, *args) -> None:
        pass

    # ruleid: python-enforce-context-manager-exit-signature
    def __aexit__(self, exc_type, exc_value, traceback):
        pass

class Good:
    # ok: python-enforce-context-manager-exit-signature
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        pass
