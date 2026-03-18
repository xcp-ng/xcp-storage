# Copyright (C) 2026  Vates SAS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import logging.handlers
import sys
from types import TracebackType

from xcp_storage.typing import (
    List,
    Optional,
    Type,
)

# ==============================================================================

_LOG_LEVEL = logging.DEBUG

_LOG_TO_STDERR = False
_LOG_TO_JOURNAL = True

# `LOG_LOCAL2` is mapped to "/var/log/SMlog".
_LOG_SYSLOG_FACILITY = logging.handlers.SysLogHandler.LOG_LOCAL2

_DEFAULT_LOGGER_NAME = "core"

# ------------------------------------------------------------------------------

def _configure_logger() -> None:
    _LOGGER.setLevel(_LOG_LEVEL)

    handlers: List[logging.Handler] = []

    if _LOG_TO_JOURNAL:
        handlers.append(logging.handlers.SysLogHandler(
            address="/dev/log",
            facility=_LOG_SYSLOG_FACILITY
        ))

    if _LOG_TO_STDERR:
        handlers.append(logging.StreamHandler(sys.stderr))

    formatter = logging.Formatter("XCP-storage: [%(process)d] - %(name)s - %(levelname)s - %(message)s")
    for handler in handlers:
        handler.setLevel(_LOG_LEVEL)
        handler.setFormatter(formatter)
        _LOGGER.addHandler(handler)

    def _excepthook(
        exception_type: Type[BaseException],
        exception_value: BaseException,
        exception_traceback: Optional[TracebackType]
    ) -> None:
        if not issubclass(exception_type, KeyboardInterrupt):
            _LOGGER.error("Unhandled exception.", exc_info=(exception_type, exception_value, exception_traceback))
        sys.__excepthook__(exception_type, exception_value, exception_traceback)
    sys.excepthook = _excepthook

# ------------------------------------------------------------------------------

_LOGGER = logging.getLogger()
_configure_logger()

# ------------------------------------------------------------------------------

def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or _DEFAULT_LOGGER_NAME)
