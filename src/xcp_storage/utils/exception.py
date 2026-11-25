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

import traceback

# ==============================================================================

def format_exception_traceback(exception: BaseException) -> str:
    """
    Return the traceback of `exception` as printed by the interpreter.
    """

    # TODO(XCPNG-3032): Pass only `exception` in python 3.10.
    return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

def stringify_exception(exception: BaseException) -> str:
    """
    Return the message of `exception`, or its type when it has none
    (raised without argument) or cannot be printed.
    Never raises.
    """

    try:
        message = str(exception)
    except Exception:
        message = ""

    if not message:
        try:
            message = f"Exception of type `{exception.__class__.__name__}`."
        except Exception:
            message = "Unknown Exception."

    return message
