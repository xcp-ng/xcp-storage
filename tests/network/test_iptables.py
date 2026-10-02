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
    _MAIN_FIREWALL_INPUT_CHAIN,
    _PROTOCOL_TCP,
    DEFAULT_FIREWALL_INPUT_CHAIN,
    IptablesError,
    update_iptables_tcp_port,
    update_iptables_tcp_port_range,
)
from xcp_storage.utils.process import CommandError, CommandResultType

from xcp_storage.typing import (
    Callable,
    cast,
    Final,
    List,
    NamedTuple,
    Optional,
    ParamSpec,
    Tuple,
    Union,
)

P = ParamSpec("P")

# ==============================================================================

def get_return_rule(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return [chain, "-j", "RETURN"]

def get_jump_rule(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return [_MAIN_FIREWALL_INPUT_CHAIN, "-j", chain]

def get_rule(
    protocol: str,
    ports_str: str,
    *,
    stateful: bool = True,
    chain: str = DEFAULT_FIREWALL_INPUT_CHAIN
) -> List[str]:
    rule = [chain, "-p", protocol]
    if stateful:
        rule += ["-m", "conntrack", "--ctstate", "NEW", "-m", protocol]
    rule += ["--dport", ports_str, "-j", "ACCEPT"]
    return rule

def get_tcp_rule(ports_str: str, *, stateful: bool = True, chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return get_rule(_PROTOCOL_TCP, ports_str, stateful=stateful, chain=chain)

# ------------------------------------------------------------------------------

def get_has_chain_cmd(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return [_EXEC_PATH_IPTABLES, "-N", chain]

def get_has_rule_cmd(rule: List[str]) -> List[str]:
    return [_EXEC_PATH_IPTABLES, "-C"] + rule

def get_add_rule_cmd(rule: List[str]) -> List[str]:
    return [_EXEC_PATH_IPTABLES, "-A"] + rule

def get_insert_rule_cmd(rule: List[str]) -> List[str]:
    return [_EXEC_PATH_IPTABLES, "-I"] + rule

def get_destroy_rule_cmd(rule: List[str]) -> List[str]:
    return [_EXEC_PATH_IPTABLES, "-D"] + rule

def get_save_iptables_cmd() -> List[str]:
    return [_EXEC_PATH_SERVICE, "iptables", "save"]

# ------------------------------------------------------------------------------

def get_has_chain_call(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call(get_has_chain_cmd(chain), simple=False)

def get_has_return_rule_call(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call(get_has_rule_cmd(get_return_rule(chain)), simple=False)

def get_add_return_rule_call(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call(get_add_rule_cmd(get_return_rule(chain)), expected_ret_code=0)

def get_has_jump_rule_call(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call(get_has_rule_cmd(get_jump_rule(chain)), simple=False)

def get_insert_jump_rule_call(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> _Call:
    return call(get_insert_rule_cmd(get_jump_rule(chain)), expected_ret_code=0)

def get_has_rule_call(rule: List[str]) -> _Call:
    return call(get_has_rule_cmd(rule), simple=False)

def get_insert_rule_call(rule: List[str]) -> _Call:
    return call(get_insert_rule_cmd(rule), expected_ret_code=0)

def get_destroy_rule_call(rule: List[str]) -> _Call:
    return call(get_destroy_rule_cmd(rule), expected_ret_code=0)

def get_save_iptables_call() -> _Call:
    return call(get_save_iptables_cmd(), expected_ret_code=0)

# ------------------------------------------------------------------------------

class PortUpdateSpec(NamedTuple):
    """
    A TCP port or range that must be tested.
    """

    tcp_rule: List[str]
    ports_arg: Union[int, Tuple[int, int]]
    target: Callable[..., None]
    open_port_arg_name: str

    def update_iptables_tcp_port(self, *, open_port: bool) -> None:
        self.target(self.ports_arg, **{self.open_port_arg_name: open_port})

TEST_SPECS: Final = [
    PortUpdateSpec(get_tcp_rule("80"), 80, update_iptables_tcp_port, "open_port"),
    PortUpdateSpec(get_tcp_rule("80:90"), (80, 90), update_iptables_tcp_port_range, "open_ports")
]

# ------------------------------------------------------------------------------

def run_command_side_effect_factory(
    *,
    has_chain: bool,
    has_return_rule: bool = False,
    has_jump_rule: bool = False,
    has_port_rule: bool = False,
    chain: str = DEFAULT_FIREWALL_INPUT_CHAIN
) -> Callable[P, CommandResultType]:
    chain_rules = {
        tuple(get_return_rule(chain)): has_return_rule,
        tuple(get_jump_rule(chain)): has_jump_rule
    }

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
            rule = cmd_args[2:] # Rule is just after `-C` flag.
            if "-p" in rule:
                return ("", "", int(not has_port_rule)) # Check for port.
            return ("", "", int(not chain_rules.get(tuple(rule), False))) # Check for return/jump.

        assert simple
        return ""
    return impl

# ------------------------------------------------------------------------------

@patch("xcp_storage.network.iptables.run_command")
@pytest.mark.parametrize("spec", TEST_SPECS)
class TestIptablesTcpPort:
    def test_open_port_without_existing_chain(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(has_chain=False)
        expected_calls = [
            get_has_rule_call(spec.tcp_rule),
            get_has_chain_call(),
            get_has_return_rule_call(),
            get_add_return_rule_call(),
            get_has_jump_rule_call(),
            get_insert_jump_rule_call(),
            get_insert_rule_call(spec.tcp_rule),
            get_save_iptables_call()
        ]

        spec.update_iptables_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_existing_chain(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=True
        )
        expected_calls = [
            get_has_rule_call(spec.tcp_rule),
            get_has_chain_call(),
            get_has_return_rule_call(),
            get_has_jump_rule_call(),
            get_insert_rule_call(spec.tcp_rule),
            get_save_iptables_call()
        ]

        spec.update_iptables_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_missing_return_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(
            has_chain=True,
            has_return_rule=False,
            has_jump_rule=True
        )
        expected_calls = [
            get_has_rule_call(spec.tcp_rule),
            get_has_chain_call(),
            get_has_return_rule_call(),
            get_add_return_rule_call(),
            get_has_jump_rule_call(),
            get_insert_rule_call(spec.tcp_rule),
            get_save_iptables_call()
        ]

        spec.update_iptables_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_missing_jump_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=False
        )
        expected_calls = [
            get_has_rule_call(spec.tcp_rule),
            get_has_chain_call(),
            get_has_return_rule_call(),
            get_has_jump_rule_call(),
            get_insert_jump_rule_call(),
            get_insert_rule_call(spec.tcp_rule),
            get_save_iptables_call()
        ]

        spec.update_iptables_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_existing_port_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=True,
            has_port_rule=True
        )
        expected_calls = [get_has_rule_call(spec.tcp_rule)]

        spec.update_iptables_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_close_port_with_existing_port_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=True,
            has_port_rule=True
        )
        expected_calls = [
            get_has_rule_call(spec.tcp_rule),
            get_destroy_rule_call(spec.tcp_rule),
            get_save_iptables_call()
        ]

        spec.update_iptables_tcp_port(open_port=False)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_close_port_without_existing_port_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=True
        )
        expected_calls = [get_has_rule_call(spec.tcp_rule)]

        spec.update_iptables_tcp_port(open_port=False)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

# ------------------------------------------------------------------------------

def run_fail_command_side_effect_factory(
    command: List[str],
    *,
    error: Optional[CommandError] = None,
    has_port_rule: bool = False
) -> Callable[P, CommandResultType]:
    default_side_effect: Callable[P, CommandResultType] = run_command_side_effect_factory(
        has_chain=False, has_port_rule=has_port_rule
    )

    def impl(*args: P.args, **kwargs: P.kwargs) -> CommandResultType:
        cmd_args = cast(List[str], args[0])
        # Mock default side effect.
        if cmd_args != command:
            return default_side_effect(*args, **kwargs)
        # Mock error.
        if error is not None:
            raise error
        # Use 3 as default error, like described by iptables manual: incompatibility between kernel and user space.
        return ("", "", cast(int, 3))
    return impl

# ------------------------------------------------------------------------------

@patch("xcp_storage.network.iptables.run_command")
@pytest.mark.parametrize("spec", TEST_SPECS)
class TestIptablesTcpPortErrors:
    def test_open_port_create_chain_fatal_code(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(get_has_chain_cmd())

        with pytest.raises(IptablesError, match="Failed to test existence of iptables chain"):
            spec.update_iptables_tcp_port(open_port=True)

    def test_open_port_has_rule_fatal_code(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(
            get_has_rule_cmd(spec.tcp_rule)
        )

        with pytest.raises(IptablesError, match="Failed to test existence of iptables rule"):
            spec.update_iptables_tcp_port(open_port=True)

    def test_open_port_has_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(
            get_has_rule_cmd(spec.tcp_rule),
            error=CommandError(None, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to test existence of iptables rule"):
            spec.update_iptables_tcp_port(open_port=True)

    def test_open_port_insert_jump_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(
            get_insert_rule_cmd(get_jump_rule()),
            error=CommandError(1, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to set up iptables chain"):
            spec.update_iptables_tcp_port(open_port=True)

    def test_open_port_insert_port_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(
            get_insert_rule_cmd(spec.tcp_rule),
            error=CommandError(1, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to open TCP port"):
            spec.update_iptables_tcp_port(open_port=True)

    def test_close_port_remove_port_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(
            get_destroy_rule_cmd(spec.tcp_rule),
            error=CommandError(1, "", reason=""),
            has_port_rule=True
        )

        with pytest.raises(IptablesError, match="Failed to close TCP port"):
            spec.update_iptables_tcp_port(open_port=False)

    def test_save_iptables_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_fail_command_side_effect_factory(
            get_save_iptables_cmd(),
            error=CommandError(1, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to save iptables changes"):
            spec.update_iptables_tcp_port(open_port=True)
