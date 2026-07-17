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

import contextlib
import typing
from typing import *  # noqa: F403

# ==============================================================================

# TODO(XCPNG-3032): Remove all hacks for python 3.11.

# Type checking is performed on recent versions of Python;
# it must be disabled to prevent workaround branches (not hasattr...)
# from being analyzed and causing errors. For example, with pyrefly and this code:
#
# ` @override
# ` def to_json(self) -> str:
# `  if self._json_payload is None:
# `         self._json_payload = json.dumps(self.payload)
# `    return self._json_payload
#
#   INFO Checking project configured at `/home/runner/work/xcp-storage/xcp-storage/pyproject.toml`
# ERROR Missing argument `self` in function `xcp_storage.utils.json.rpc.JsonRpcResponse.to_json` [missing-argument]
#   --> tests/utils/test_json_rpc.py:49:75
if not TYPE_CHECKING:  # noqa: F405
    if not hasattr(typing, "Final"):
        from typing_extensions import Final  # noqa: F401

    if not hasattr(typing, "override"):
        def override(method):  # type: ignore # noqa: ANN001, ANN201
            with contextlib.suppress(AttributeError, TypeError):
                # Set internal attr `__override__` like described in PEP 698.
                method.__override__ = True
            return method

    if not hasattr(typing, "Never"):
        Never = None  # type: ignore

    if not hasattr(typing, "Literal"):
        from typing_extensions import Literal  # noqa: F401, UP035

    if not hasattr(typing, "ParamSpec"):
        class _SubscriptableListMock(list):
            def __getitem__(self, _):  # type: ignore # noqa: ANN001, ANN204
                return self

            def __getattr__(self, _):  # type: ignore # noqa: ANN001, ANN204
                return self

            def __call__(self, *_args, **_kwargs):  # type: ignore # noqa: ANN002, ANN003, ANN204
                return self

        ParamSpec = _SubscriptableListMock()  # type: ignore
        Concatenate = _SubscriptableListMock()  # type: ignore
