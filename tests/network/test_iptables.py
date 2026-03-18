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

from unittest.mock import (
    _Call,
    call,
    MagicMock,
    patch,
)

import pytest

from xcp_storage.network.iptables import (
    _EXEC_PATH_IPTABLES,
    _EXEC_PATH_SERVICE,
    _PROTOCOL_TCP,
    DEFAULT_FIREWALL_INPUT_CHAIN,
    update_iptables_tcp_port,
)
from xcp_storage.utils.process import CommandResultType

from xcp_storage.typing import (
    Callable,
    cast,
    List,
    Optional,
    ParamSpec,
)

P = ParamSpec("P")

# ==============================================================================

def get_rule(
    protocol: str,
    str_ports: str,
    *,
    stateful: bool = True,
    chain: str = DEFAULT_FIREWALL_INPUT_CHAIN
) -> List[str]:
    rule = [chain, "-p", protocol]
    if stateful:
        rule += ["-m", "conntrack", "--ctstate", "NEW", "-m", protocol]
    rule += ["--dport", str_ports, "-j", "ACCEPT"]
    return rule

def get_tcp_rule(str_ports: str, *, stateful: bool = True, chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return get_rule(_PROTOCOL_TCP, str_ports, stateful=stateful, chain=chain)

# ------------------------------------------------------------------------------

def get_has_chain_call(chain: Optional[str] = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call([_EXEC_PATH_IPTABLES, "-N", chain], simple=False)

def get_add_chain_call(chain: Optional[str] = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call([_EXEC_PATH_IPTABLES, "-A", chain, "-j", "RETURN"], expected_ret_code=0)

def get_insert_chain_call(chain: Optional[str] = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call([_EXEC_PATH_IPTABLES, "-I", "INPUT", "-j", chain], expected_ret_code=0)

def get_has_rule_call(rule: List[str]) -> _Call:
    return call([_EXEC_PATH_IPTABLES, "-C"] + rule, simple=False)

def get_insert_rule_call(rule: List[str]) -> _Call:
    return call([_EXEC_PATH_IPTABLES, "-I"] + rule, expected_ret_code=0)

def get_destroy_rule_call(rule: List[str]) -> _Call:
    return call([_EXEC_PATH_IPTABLES, "-D"] + rule, expected_ret_code=0)

def get_save_iptables_call() -> _Call:
    return call([_EXEC_PATH_SERVICE, "iptables", "save"], expected_ret_code=0)

# ------------------------------------------------------------------------------

def run_command_side_effect_factory(*, has_chain: bool, has_rule: bool) -> Callable[P, CommandResultType]:
    def impl(*args: P.args, **kwargs: P.kwargs) -> CommandResultType:
        cmd_args = cast(List[str], args[0])

        program_name = cmd_args[0]
        assert program_name in (_EXEC_PATH_IPTABLES, _EXEC_PATH_SERVICE)

        simple = kwargs.get("simple", True)

        # Has chain?
        if "-N" in cmd_args:
            assert not simple
            return ("", "", int(has_chain))

        # Has rule?
        if "-C" in cmd_args:
            assert not simple
            return ("", "", int(not has_rule))

        assert simple
        return ""
    return impl

# ------------------------------------------------------------------------------

@patch("xcp_storage.network.iptables.run_command")
class TestIptablesTcpPort:
    TEST_PORT = 80
    TEST_RULE = get_tcp_rule(str(TEST_PORT))

    @pytest.mark.parametrize("open_port", (True, False))
    def test_update_port_no_change(self, mock_run_command: MagicMock, *, open_port: bool) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(has_chain=True, has_rule=open_port)
        update_iptables_tcp_port(self.TEST_PORT, open_port=open_port)
        has_rule_call = get_has_rule_call(self.TEST_RULE)
        mock_run_command.assert_called_once_with(*has_rule_call.args, **has_rule_call.kwargs)

    def test_open_tcp_port(self, mock_run_command: MagicMock) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(has_chain=True, has_rule=False)
        expected_calls = [
            get_has_rule_call(self.TEST_RULE),
            get_has_chain_call(),
            get_insert_rule_call(self.TEST_RULE),
            get_save_iptables_call()
        ]

        update_iptables_tcp_port(self.TEST_PORT, open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_and_create_chain(self, mock_run_command: MagicMock) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(has_chain=False, has_rule=False)
        expected_calls = [
            get_has_rule_call(self.TEST_RULE),
            get_has_chain_call(),
            get_add_chain_call(),
            get_insert_chain_call(),
            get_insert_rule_call(self.TEST_RULE),
            get_save_iptables_call()
        ]

        update_iptables_tcp_port(self.TEST_PORT, open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_close_port(self, mock_run_command: MagicMock) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(has_chain=False, has_rule=True)
        expected_calls = [
            get_has_rule_call(self.TEST_RULE),
            get_destroy_rule_call(self.TEST_RULE),
            get_save_iptables_call()
        ]

        update_iptables_tcp_port(self.TEST_PORT, open_port=False)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)
