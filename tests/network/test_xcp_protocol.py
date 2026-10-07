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

import pytest

from xcp_storage.network.protocol.xcp import XcpProtocol

# ==============================================================================

class TestXcpProtocolSeq:
    @pytest.mark.parametrize(("seq", "expected_next_seq"), [
        (0, 1),
        (1, 2),
        (XcpProtocol.MAX_SEQ - 1, XcpProtocol.MAX_SEQ),
        (XcpProtocol.MAX_SEQ, 1)
    ])
    def test_next(self, seq: int, expected_next_seq: int) -> None:
        assert XcpProtocol().get_next_packet_seq(seq) == expected_next_seq

    def test_bounds(self) -> None:
        protocol = XcpProtocol()

        seq = 0
        for _ in range(2 * XcpProtocol.MAX_SEQ):
            seq = protocol.get_next_packet_seq(seq)
            assert 1 <= seq <= XcpProtocol.MAX_SEQ
