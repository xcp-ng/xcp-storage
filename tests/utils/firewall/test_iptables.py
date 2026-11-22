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

from pathlib import Path
from unittest.mock import (
    _Call,
    ANY,
    call,
    MagicMock,
    patch,
)

import pytest

from tests.utils.exception import raises_exactly
from xcp_storage.utils.firewall.iptables import (
    _EXEC_PATH_IPTABLES,
    _EXEC_PATH_IPTABLES_RESTORE,
    _EXEC_PATH_SERVICE,
    _MAIN_FIREWALL_INPUT_CHAIN,
    _PROTOCOL_TCP,
    DEFAULT_FIREWALL_INPUT_CHAIN,
    IptablesError,
    IptablesFirewallBackend,
)
from xcp_storage.utils.process import CommandError, CommandResult, RunCommandResult

from xcp_storage.typing import (
    Callable,
    cast,
    Final,
    Iterator,
    List,
    NamedTuple,
    Optional,
    ParamSpec,
    Sequence,
    Tuple,
    Union,
)

P = ParamSpec("P")

# ==============================================================================

_IPTABLES_MODULE: Final = IptablesFirewallBackend.__module__

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_run_command() -> Iterator[MagicMock]:
    with patch(f"{_IPTABLES_MODULE}.run_command", autospec=True) as mock_run_command:
        yield mock_run_command

# ------------------------------------------------------------------------------

def get_return_rule(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return [chain, "-j", "RETURN"]

def get_jump_rule(chain: str = DEFAULT_FIREWALL_INPUT_CHAIN) -> List[str]:
    return [_MAIN_FIREWALL_INPUT_CHAIN, "-j", chain]

def get_rule(
    protocol: str,
    ports_str: str,
    *,
    stateful: bool = True,
    chain: str = DEFAULT_FIREWALL_INPUT_CHAIN,
    target_chain: Optional[str] = None
) -> List[str]:
    rule = [chain, "-p", protocol]
    if stateful:
        rule += ["-m", "conntrack", "--ctstate", "NEW", "-m", protocol]
    rule += ["--dport", ports_str, "-j", target_chain or "ACCEPT"]
    return rule

def get_tcp_rule(
    ports_str: str,
    *,
    stateful: bool = True,
    chain: str = DEFAULT_FIREWALL_INPUT_CHAIN,
    target_chain: Optional[str] = None
) -> List[str]:
    return get_rule(_PROTOCOL_TCP, ports_str, stateful=stateful, chain=chain, target_chain=target_chain)

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

# Allowlist chain (`PortUpdateSpec.allowlist`), and its addresses.
ALLOWLIST_CHAIN: Final = "test-hosts"
ALLOWLIST_ADDRESSES: Final = ("10.30.43.1", "10.30.43.2")

# Empty, too long, separators, starting with `-`.
INVALID_CHAIN_NAMES: Final = ("", "x" * 29, "a b", "a\nCOMMIT", "-F")

class PortUpdateSpec(NamedTuple):
    """
    A TCP port or range that must be tested, open to any address, or to the allowlist chain `allowlist`.
    """

    tcp_rule: List[str]
    ports_arg: Union[int, Tuple[int, int]]
    target: Callable[..., None]
    open_port_arg_name: str
    allowlist: Optional[str] = None

    def update_tcp_port(self, *, open_port: bool) -> None:
        self.update_tcp_port_to(self.allowlist, open_port=open_port)

    def update_tcp_port_to(self, allowlist: Optional[str], *, open_port: bool) -> None:
        self.target(
            IptablesFirewallBackend(),
            self.ports_arg,
            **{self.open_port_arg_name: open_port},
            stateful=True,
            allowlist=allowlist
        )

TEST_SPECS: Final = [
    PortUpdateSpec(get_tcp_rule("80"), 80, IptablesFirewallBackend.update_tcp_port, "open_port"),
    PortUpdateSpec(get_tcp_rule("80:90"), (80, 90), IptablesFirewallBackend.update_tcp_port_range, "open_ports"),
    PortUpdateSpec(
        get_tcp_rule("80", target_chain=ALLOWLIST_CHAIN),
        80,
        IptablesFirewallBackend.update_tcp_port,
        "open_port",
        ALLOWLIST_CHAIN
    ),
    PortUpdateSpec(
        get_tcp_rule("80:90", target_chain=ALLOWLIST_CHAIN),
        (80, 90),
        IptablesFirewallBackend.update_tcp_port_range,
        "open_ports",
        ALLOWLIST_CHAIN
    ),
]

# ------------------------------------------------------------------------------

def run_port_command_side_effect_factory(
    *,
    has_chain: bool,
    has_return_rule: bool = False,
    has_jump_rule: bool = False,
    has_port_rule: bool = False,
    chain: str = DEFAULT_FIREWALL_INPUT_CHAIN
) -> Callable[P, RunCommandResult]:
    chain_rules = {
        tuple(get_return_rule(chain)): has_return_rule,
        tuple(get_jump_rule(chain)): has_jump_rule
    }

    def impl(*args: P.args, **kwargs: P.kwargs) -> RunCommandResult:
        cmd_args = cast(List[str], args[0])

        program_name = cmd_args[0]
        assert program_name in (_EXEC_PATH_IPTABLES, _EXEC_PATH_SERVICE)

        simple = kwargs.get("simple", True)

        # Has chain?
        if "-N" in cmd_args:
            assert not simple
            return CommandResult(ret_code=int(has_chain))

        # Has rule?
        if "-C" in cmd_args:
            assert not simple
            rule = cmd_args[2:] # Rule is just after `-C` flag.
            if "-p" in rule:
                return CommandResult(ret_code=int(not has_port_rule)) # Check for port.
            return CommandResult(ret_code=int(not chain_rules.get(tuple(rule), False))) # Check for return/jump.

        assert simple
        return ""
    return impl

# ------------------------------------------------------------------------------

@pytest.mark.parametrize("spec", TEST_SPECS)
class TestIptablesTcpPort:
    def test_open_port_without_existing_chain(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(has_chain=False)
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

        spec.update_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_existing_chain(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(
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

        spec.update_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_missing_return_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(
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

        spec.update_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_missing_jump_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(
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

        spec.update_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_open_port_with_existing_port_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=True,
            has_port_rule=True
        )
        expected_calls = [get_has_rule_call(spec.tcp_rule)]

        spec.update_tcp_port(open_port=True)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_close_port_with_existing_port_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(
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

        spec.update_tcp_port(open_port=False)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

    def test_close_port_without_existing_port_rule(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_command_side_effect_factory(
            has_chain=True,
            has_return_rule=True,
            has_jump_rule=True
        )
        expected_calls = [get_has_rule_call(spec.tcp_rule)]

        spec.update_tcp_port(open_port=False)

        mock_run_command.assert_has_calls(expected_calls)
        assert mock_run_command.call_count == len(expected_calls)

# ------------------------------------------------------------------------------

def run_port_fail_command_side_effect_factory(
    command: List[str],
    *,
    error: Optional[CommandError] = None,
    has_port_rule: bool = False
) -> Callable[P, RunCommandResult]:
    default_side_effect: Callable[P, RunCommandResult] = run_port_command_side_effect_factory(
        has_chain=False, has_port_rule=has_port_rule
    )

    def impl(*args: P.args, **kwargs: P.kwargs) -> RunCommandResult:
        cmd_args = cast(List[str], args[0])
        # Mock default side effect.
        if cmd_args != command:
            return default_side_effect(*args, **kwargs)
        # Mock error.
        if error is not None:
            raise error
        # Use 3 as default error, like described by iptables manual: incompatibility between kernel and user space.
        return CommandResult(ret_code=3)
    return impl

# ------------------------------------------------------------------------------

@pytest.mark.parametrize("spec", TEST_SPECS)
class TestIptablesTcpPortErrors:
    def test_open_port_create_chain_fatal_code(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(get_has_chain_cmd())

        with pytest.raises(IptablesError, match="Failed to test existence of iptables chain"):
            spec.update_tcp_port(open_port=True)

    def test_open_port_has_rule_fatal_code(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(
            get_has_rule_cmd(spec.tcp_rule)
        )

        with pytest.raises(IptablesError, match="Failed to test existence of iptables rule"):
            spec.update_tcp_port(open_port=True)

    def test_open_port_has_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(
            get_has_rule_cmd(spec.tcp_rule),
            error=CommandError(None, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to test existence of iptables rule"):
            spec.update_tcp_port(open_port=True)

    def test_open_port_insert_jump_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(
            get_insert_rule_cmd(get_jump_rule()),
            error=CommandError(1, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to set up iptables chain"):
            spec.update_tcp_port(open_port=True)

    def test_open_port_insert_port_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(
            get_insert_rule_cmd(spec.tcp_rule),
            error=CommandError(1, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to open TCP port"):
            spec.update_tcp_port(open_port=True)

    def test_close_port_remove_port_rule_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(
            get_destroy_rule_cmd(spec.tcp_rule),
            error=CommandError(1, "", reason=""),
            has_port_rule=True
        )

        with pytest.raises(IptablesError, match="Failed to close TCP port"):
            spec.update_tcp_port(open_port=False)

    def test_save_iptables_command_error(self, mock_run_command: MagicMock, spec: PortUpdateSpec) -> None:
        mock_run_command.side_effect = run_port_fail_command_side_effect_factory(
            get_save_iptables_cmd(),
            error=CommandError(1, "", reason="")
        )

        with pytest.raises(IptablesError, match="Failed to save iptables changes"):
            spec.update_tcp_port(open_port=True)

    @pytest.mark.parametrize("allowlist", INVALID_CHAIN_NAMES)
    def test_invalid_allowlist(self, mock_run_command: MagicMock, spec: PortUpdateSpec, allowlist: str) -> None:
        with raises_exactly(ValueError, f"Invalid iptables chain name: `{allowlist}`."):
            spec.update_tcp_port_to(allowlist, open_port=True)
        mock_run_command.assert_not_called()

# ------------------------------------------------------------------------------

class TestAllowlistChain:
    LIST_CHAIN_CALL: Final = call([_EXEC_PATH_IPTABLES, "-S", ALLOWLIST_CHAIN], simple=False)

    @pytest.fixture
    def chain_listing(self) -> List[CommandResult]:
        # Result of `iptables -S <chain>`, set by the test: the chain is missing by default.
        return [CommandResult(stderr="iptables: No chain/target/match by that name.", ret_code=1)]

    @pytest.fixture
    def iptables_restore_rules(self, mock_run_command: MagicMock, chain_listing: List[CommandResult]) -> List[str]:
        # Input files given to `iptables-restore`, read during the call: removed after it.
        iptables_restore_rules: List[str] = []

        def run_command(args: List[str], **_kwargs: object) -> RunCommandResult:
            if args[0] == _EXEC_PATH_IPTABLES and args[1] == "-S":
                return chain_listing[0]
            if args[0] == _EXEC_PATH_IPTABLES_RESTORE:
                iptables_restore_rules.append(Path(args[-1]).read_text())
            return ""

        mock_run_command.side_effect = run_command
        return iptables_restore_rules

    @staticmethod
    def get_allowlist_chain_rules_result(addresses: Sequence[str]) -> CommandResult:
        # `iptables -S` of a chain accepting `addresses`.
        rules = "".join(f"-A {ALLOWLIST_CHAIN} -s {address}/32 -j ACCEPT\n" for address in addresses)
        return CommandResult(stdout=f"-N {ALLOWLIST_CHAIN}\n{rules}")

    @staticmethod
    def get_allowlist_chain_restore_rules(addresses: Sequence[str], chain: str = ALLOWLIST_CHAIN) -> str:
        # Input of `iptables-restore` replacing the chain `chain` by a chain accepting `addresses`.
        rules = "".join(f"-A {chain} -s {address} -j ACCEPT\n" for address in addresses)
        return f"*filter\n:{chain} - [0:0]\n{rules}COMMIT\n"

    @pytest.mark.usefixtures("iptables_restore_rules")
    def test_create(self, mock_run_command: MagicMock) -> None:
        # Missing: created empty, saved.
        IptablesFirewallBackend().create_allowlist(ALLOWLIST_CHAIN)
        assert mock_run_command.call_args_list == [
            self.LIST_CHAIN_CALL,
            call([_EXEC_PATH_IPTABLES, "-N", ALLOWLIST_CHAIN], expected_ret_code=0),
            get_save_iptables_call()
        ]

    def test_create_existing(self, mock_run_command: MagicMock, chain_listing: List[CommandResult]) -> None:
        # Kept as it is.
        chain_listing[0] = self.get_allowlist_chain_rules_result(ALLOWLIST_ADDRESSES)
        mock_run_command.side_effect = [chain_listing[0]]
        IptablesFirewallBackend().create_allowlist(ALLOWLIST_CHAIN)
        assert mock_run_command.call_args_list == [self.LIST_CHAIN_CALL]

    def test_create_error(self, mock_run_command: MagicMock, chain_listing: List[CommandResult]) -> None:
        mock_run_command.side_effect = [chain_listing[0], CommandError(1, "", reason="boom")]
        with raises_exactly(IptablesError, f"Failed to create iptables allowlist chain `{ALLOWLIST_CHAIN}`: `boom`."):
            IptablesFirewallBackend().create_allowlist(ALLOWLIST_CHAIN)

    def test_create_invalid_chain(self, mock_run_command: MagicMock) -> None:
        with raises_exactly(ValueError, f"Invalid iptables chain name: `{_MAIN_FIREWALL_INPUT_CHAIN}`."):
            IptablesFirewallBackend().create_allowlist(_MAIN_FIREWALL_INPUT_CHAIN)
        mock_run_command.assert_not_called()

    def test_update(self, mock_run_command: MagicMock, iptables_restore_rules: List[str]) -> None:
        IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, ALLOWLIST_ADDRESSES)
        assert iptables_restore_rules == [self.get_allowlist_chain_restore_rules(ALLOWLIST_ADDRESSES)]
        assert mock_run_command.call_args_list == [
            self.LIST_CHAIN_CALL,
            call([_EXEC_PATH_IPTABLES_RESTORE, "--noflush", ANY], expected_ret_code=0),
            get_save_iptables_call()
        ]
        # A temporary file, removed.
        assert not Path(mock_run_command.call_args_list[1][0][0][-1]).exists()

    def test_no_update(
        self, mock_run_command: MagicMock, chain_listing: List[CommandResult], iptables_restore_rules: List[str]
    ) -> None:
        # The same addresses, whatever their order: neither replaced nor saved.
        chain_listing[0] = self.get_allowlist_chain_rules_result(ALLOWLIST_ADDRESSES[::-1])
        IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, ALLOWLIST_ADDRESSES)
        assert iptables_restore_rules == []
        assert mock_run_command.call_args_list == [self.LIST_CHAIN_CALL]

    @pytest.mark.parametrize("current_addresses", [
        pytest.param(ALLOWLIST_ADDRESSES[:1], id="missing-address"),
        pytest.param((*ALLOWLIST_ADDRESSES, "10.30.43.99"), id="other-address"),
        pytest.param((), id="empty"),
    ])
    def test_replace_and_update(
        self,
        chain_listing: List[CommandResult],
        iptables_restore_rules: List[str],
        current_addresses: Sequence[str]
    ) -> None:
        chain_listing[0] = self.get_allowlist_chain_rules_result(current_addresses)
        # Replaced as a whole: the addresses not given are removed.
        IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, ALLOWLIST_ADDRESSES)
        assert iptables_restore_rules == [self.get_allowlist_chain_restore_rules(ALLOWLIST_ADDRESSES)]

    def test_update_without_address(self, iptables_restore_rules: List[str]) -> None:
        IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, [])
        assert iptables_restore_rules == [self.get_allowlist_chain_restore_rules([])]

    def test_update_with_invalid_address(self, mock_run_command: MagicMock) -> None:
        with raises_exactly(ValueError, "Invalid IPv4 address: `stor-1`."):
            IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, [ALLOWLIST_ADDRESSES[0], "stor-1"])
        mock_run_command.assert_not_called()

    @pytest.mark.parametrize("chain", [*INVALID_CHAIN_NAMES, _MAIN_FIREWALL_INPUT_CHAIN, DEFAULT_FIREWALL_INPUT_CHAIN])
    def test_update_with_invalid_chain(self, mock_run_command: MagicMock, chain: str) -> None:
        with raises_exactly(ValueError, f"Invalid iptables chain name: `{chain}`."):
            IptablesFirewallBackend().update_allowlist(chain, ALLOWLIST_ADDRESSES)
        mock_run_command.assert_not_called()

    def test_update_with_longest_chain(self, iptables_restore_rules: List[str]) -> None:
        chain = "x" * 28
        IptablesFirewallBackend().update_allowlist(chain, ALLOWLIST_ADDRESSES)
        assert iptables_restore_rules == [self.get_allowlist_chain_restore_rules(ALLOWLIST_ADDRESSES, chain)]

    def test_update_read_fatal_code(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(stderr="boom", ret_code=3)
        with raises_exactly(IptablesError, f"Failed to read iptables chain `{ALLOWLIST_CHAIN}`: `boom`.") as exc_info:
            IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, ALLOWLIST_ADDRESSES)
        assert exc_info.value.code == 3

    def test_update_read_command_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.side_effect = CommandError(3, "", reason="boom")
        with raises_exactly(IptablesError, f"Failed to read iptables chain `{ALLOWLIST_CHAIN}`: `boom`.") as exc_info:
            IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, ALLOWLIST_ADDRESSES)
        assert exc_info.value.code == 3

    def test_restore_error(self, mock_run_command: MagicMock, chain_listing: List[CommandResult]) -> None:
        # Nothing saved.
        mock_run_command.side_effect = [chain_listing[0], CommandError(2, "", reason="boom")]
        with raises_exactly(
            IptablesError, f"Failed to update iptables allowlist chain `{ALLOWLIST_CHAIN}`: `boom`."
        ) as exc_info:
            IptablesFirewallBackend().update_allowlist(ALLOWLIST_CHAIN, ALLOWLIST_ADDRESSES)
        assert exc_info.value.code == 2
        assert mock_run_command.call_count == 2
