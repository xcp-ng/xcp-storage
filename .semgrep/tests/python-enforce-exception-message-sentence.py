# ------------------------------------------------------------------------------
# String literal messages.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exception-message-sentence
raise ValueError("invalid value.")
# ruleid: python-enforce-exception-message-sentence
raise LockError("Invalid value")
# ruleid: python-enforce-exception-message-sentence
raise errors.SocketError(f"bad {x}.")
# ok: python-enforce-exception-message-sentence
raise ValueError("Invalid value.")
# ok: python-enforce-exception-message-sentence
raise ValueError(f"`{x}` is invalid!")

# ------------------------------------------------------------------------------
# Out of scope: dynamic message, not an exception class.
# ------------------------------------------------------------------------------

# ok: python-enforce-exception-message-sentence
raise ValueError(message)
# ok: python-enforce-exception-message-sentence
raise CommandError(code, str(args), reason="x")
# ok: python-enforce-exception-message-sentence
raise NotAnErrorClass("lower")
