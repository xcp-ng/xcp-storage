# ------------------------------------------------------------------------------
# `__enter__` and `__aenter__` signatures.
# ------------------------------------------------------------------------------

class Bad:
    # ruleid: python-enforce-context-manager-enter-signature
    def __enter__(self):
        return self

    # ruleid: python-enforce-context-manager-enter-signature
    def __aenter__(self, extra) -> "Bad":
        return self

class Good:
    # ok: python-enforce-context-manager-enter-signature
    def __enter__(self) -> "Good":
        return self

    # ok: python-enforce-context-manager-enter-signature
    async def __aenter__(self) -> "Good":
        return self
