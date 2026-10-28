# ------------------------------------------------------------------------------
# Level given as a string.
# ------------------------------------------------------------------------------

def test_levels(caplog) -> None:
    # ruleid: python-enforce-log-level-constant
    with caplog.at_level("DEBUG"):
        pass
    # ruleid: python-enforce-log-level-constant
    caplog.at_level(level="WARNING")
    # ruleid: python-enforce-log-level-constant
    caplog.set_level('INFO', logger="x")
    # ruleid: python-enforce-log-level-constant
    caplog.set_level(level="DEBUG")
    # ruleid: python-enforce-log-level-constant
    logger.setLevel("ERROR")
    # ok: python-enforce-log-level-constant
    caplog.set_level(log.DEBUG)
    # ok: python-enforce-log-level-constant
    caplog.at_level(log.INFO, logger="x")
    # ok: python-enforce-log-level-constant
    caplog.set_level("VERBOSE")
