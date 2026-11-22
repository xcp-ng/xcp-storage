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

import ipaddress
import re

from xcp_storage.config.platform import DEFAULT_FIREWALL_INPUT_CHAIN
from xcp_storage.utils.check import check_ipv4_address, check_regex_match
from xcp_storage.utils.file import create_temporary_directory
from xcp_storage.utils.firewall.interface import FirewallBackend, FirewallError
from xcp_storage.utils.process import CommandError, CommandResult, run_command

from xcp_storage.typing import (
    Final,
    List,
    Optional,
    override,
    Sequence,
    Tuple,
)

# ==============================================================================

_MAIN_FIREWALL_INPUT_CHAIN: Final = "INPUT"

_EXEC_PATH_IPTABLES: Final = "/usr/sbin/iptables"
_EXEC_PATH_IPTABLES_RESTORE: Final = "/usr/sbin/iptables-restore"
_EXEC_PATH_SERVICE: Final = "/usr/sbin/service"

_PROTOCOL_TCP: Final = "tcp"

# Table of the chains of this module, the default one of `iptables`.
_IPTABLES_FILTER_TABLE: Final = "filter"

# Name of a chain given to `iptables`.
_CHAIN_NAME_REGEX: Final = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_.-]{0,27}")

# ------------------------------------------------------------------------------

class IptablesError(FirewallError):
    pass

# ------------------------------------------------------------------------------

def _save_iptables_changes() -> None:
    try:
        run_command([_EXEC_PATH_SERVICE, "iptables", "save"], expected_ret_code=0)
    except CommandError as e:
        raise IptablesError(f"Failed to save iptables changes: `{e.reason}`.", e.code) from None

# ------------------------------------------------------------------------------

def _run_iptables_command(flag: str, rule: List[str]) -> None:
    run_command([_EXEC_PATH_IPTABLES, flag] + rule, expected_ret_code=0)

def _try_iptables_command(flag: str, rule: List[str]) -> CommandResult:
    return run_command([_EXEC_PATH_IPTABLES, flag] + rule, simple=False)

# ------------------------------------------------------------------------------

def _is_fatal_iptables_code(code: int) -> bool:
    # Documented by manual of iptables:
    # 0 for correct exit.
    # 2 for invalid command.
    # 3 for incompatibility between kernel and user space.
    # 4 for busy lock, failing memory allocation or error messages from kernel.
    # 1 for other errors.
    return code not in (0, 1)

def _check_iptables_chain_name(chain: str) -> None:
    check_regex_match(chain, _CHAIN_NAME_REGEX, "iptables chain name")

# ------------------------------------------------------------------------------

def _get_iptables_chain_rules(chain: str) -> Optional[List[str]]:
    # Rules of the chain `chain` as printed by `iptables -S` (`-A <chain> ...`), `None` if it does not exist.
    code: Optional[int]
    try:
        stdout, reason, code = _try_iptables_command("-S", [chain])
        if not _is_fatal_iptables_code(code):
            return None if code else [line for line in stdout.splitlines() if line.startswith("-A ")]
    except CommandError as e:
        reason, code = e.reason, e.code
    raise IptablesError(f"Failed to read iptables chain `{chain}`: `{reason}`.", code)

# ------------------------------------------------------------------------------

def _ensure_iptables_input_chain_exists(chain: str) -> bool:
    try:
        _stdout, stderr, ret_code = _try_iptables_command("-N", [chain])
        if _is_fatal_iptables_code(ret_code):
            raise IptablesError(f"Failed to test existence of iptables chain `{chain}`: `{stderr}`.", ret_code)
        updated = not ret_code

        return_rule = [chain, "-j", "RETURN"]
        if not _has_iptables_rule(return_rule):
            _run_iptables_command("-A", return_rule)
            updated = True

        jump_rule = [_MAIN_FIREWALL_INPUT_CHAIN, "-j", chain]
        if not _has_iptables_rule(jump_rule):
            _run_iptables_command("-I", jump_rule)
            updated = True
    except CommandError as e:
        raise IptablesError(f"Failed to set up iptables chain `{chain}`: `{e.reason}`.", e.code) from None
    return updated

# ------------------------------------------------------------------------------

def _has_iptables_rule(rule: List[str]) -> bool:
    code: Optional[int]
    try:
        _stdout, reason, code = _try_iptables_command("-C", rule)
        if not _is_fatal_iptables_code(code):
            return not code
    except CommandError as e:
        reason, code = e.reason, e.code
    raise IptablesError(f"Failed to test existence of iptables rule `{rule}`: `{reason}`.", code)

# ------------------------------------------------------------------------------

# Open/close TCP port using stateless or stateful rule.
#
# /!\ When opening or closing TCP ports using stateful rules, be aware of the Linux `conntrack` mechanism:
# it maintains a state database of all network connections (TCP, UDP, ...) passing through a machine.
# This is important for packet filtering, but there is a limitation:
# The kernel sets a maximum limit `nf_conntrack_max` based on available RAM.
# If this limit is reached, the system will log:
# `nf_conntrack: table full, dropping packets`
# and and start rejecting incoming/outgoing traffic...
#
# Even after a connection is closed, the kernel retains the entry in the table for a long period,
# 120 seconds for TCP.
#
# So it's important to avoid `conntrack` for specific case like DRBD protocol.
# For it, that's important to allow packets to pass even when the connection tracking table
# ran full temporarily because short-lived connections are the primary cause of table exhaustion
# AND because we can have this scenario with DRBD.

def _update_iptables_ports(
    protocol: str,
    str_ports: str,
    *,
    open_ports: bool,
    stateful: bool,
    target_chain: Optional[str]
) -> None:
    # `target_chain`: the rule of the port jumps to this chain instead of
    # accepting the packets.

    if target_chain is not None:
        _check_iptables_chain_name(target_chain)

    # 1. Check if the rule is present.
    chain = DEFAULT_FIREWALL_INPUT_CHAIN
    rule = [chain, "-p", protocol]
    if stateful:
        rule += ["-m", "conntrack", "--ctstate", "NEW", "-m", protocol]
    rule += ["--dport", str_ports, "-j", target_chain or "ACCEPT"]

    if open_ports == _has_iptables_rule(rule):
        return

    # 2. Open or close.
    if open_ports:
        _ensure_iptables_input_chain_exists(chain)
        try:
            _run_iptables_command("-I", rule)
        except CommandError as e:
            raise IptablesError(
                f"Failed to open {protocol.upper()} port(s): `{e.reason}`.", e.code
            ) from None
    else:
        try:
            _run_iptables_command("-D", rule)
        except CommandError as e:
            raise IptablesError(
                f"Failed to close {protocol.upper()} port(s): `{e.reason}`.", e.code
            ) from None

    # 3. Save.
    _save_iptables_changes()

# ------------------------------------------------------------------------------

def _check_allowlist_chain_name(chain: str) -> None:
    _check_iptables_chain_name(chain)
    if chain in (_MAIN_FIREWALL_INPUT_CHAIN, DEFAULT_FIREWALL_INPUT_CHAIN):
        raise ValueError(f"Invalid iptables chain name: `{chain}`.")

def _build_allowlist_chain_rule(chain: str, source: str) -> str:
    # Rule of an allowlist chain (`update_allowlist`) accepting the address `source` (canonical form), as printed
    # by `iptables -S`: with the prefix length.
    return f"-A {chain} -s {source}/32 -j ACCEPT"

# ------------------------------------------------------------------------------

class IptablesFirewallBackend(FirewallBackend):
    """
    Firewall managed by `iptables`: the rules of the ports are in the chain `DEFAULT_FIREWALL_INPUT_CHAIN`.
    An allowlist is a chain of rules accepting one address each, jumped to by the rules of the ports open to it.
    """

    @override
    def update_tcp_port(self, port: int, *, open_port: bool, stateful: bool, allowlist: Optional[str]) -> None:
        _update_iptables_ports(
            _PROTOCOL_TCP,
            str(port),
            open_ports=open_port,
            stateful=stateful,
            target_chain=allowlist
        )

    @override
    def update_tcp_port_range(
        self, ports: Tuple[int, int], *, open_ports: bool, stateful: bool, allowlist: Optional[str]
    ) -> None:
        _update_iptables_ports(
            _PROTOCOL_TCP,
            f"{ports[0]}:{ports[1]}",
            open_ports=open_ports,
            stateful=stateful,
            target_chain=allowlist
        )

    @override
    def create_allowlist(self, name: str) -> None:
        _check_allowlist_chain_name(name)
        if _get_iptables_chain_rules(name) is not None:
            return

        try:
            _run_iptables_command("-N", [name])
        except CommandError as e:
            raise IptablesError(f"Failed to create iptables allowlist chain `{name}`: `{e.reason}`.", e.code) from None

        _save_iptables_changes()

    @override
    def update_allowlist(self, name: str, addresses: Sequence[str]) -> None:
        """
        Implementation: the rules of the chain `name` are replaced at once (`iptables-restore --noflush`: all or
        nothing, the other chains untouched), then saved with the others.
        """

        _check_allowlist_chain_name(name)
        for address in addresses:
            check_ipv4_address(address, "IPv4 address")

        sources = [str(ipaddress.IPv4Address(address)) for address in addresses]

        expected_rules = {_build_allowlist_chain_rule(name, source) for source in sources}
        current_rules = _get_iptables_chain_rules(name)
        if current_rules is not None and set(current_rules) == expected_rules:
            return

        rules = [f"*{_IPTABLES_FILTER_TABLE}", f":{name} - [0:0]"]
        rules += [f"-A {name} -s {source} -j ACCEPT" for source in sources]
        rules.append("COMMIT")

        with create_temporary_directory() as tmp_dir_path:
            rules_path = tmp_dir_path / "rules"
            rules_path.write_text("\n".join(rules) + "\n")
            try:
                run_command([_EXEC_PATH_IPTABLES_RESTORE, "--noflush", str(rules_path)], expected_ret_code=0)
            except CommandError as e:
                raise IptablesError(
                    f"Failed to update iptables allowlist chain `{name}`: `{e.reason}`.", e.code
                ) from None

        _save_iptables_changes()
