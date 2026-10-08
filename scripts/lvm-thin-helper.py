#!/usr/bin/env python3
#
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

import argparse
from dataclasses import dataclass
import json
import logging
from pathlib import Path

import xcp_storage.log as log
from xcp_storage.utils.json import JsonDict
from xcp_storage.utils.process import run_command

from xcp_storage.typing import Optional

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

def _parse_fullreport(vg_name: str, file_path: Optional[Path]) -> JsonDict:
    if file_path:
        with file_path.open() as file:
            fullreport_str = file.read()
    else:
        fullreport_str = run_command([
            "lvm", "fullreport", "--reportformat", "json", vg_name
        ], expected_ret_code=0)

    fullreport = json.loads(fullreport_str)

    if len(fullreport["report"]) != 1:
        raise ValueError("The lvm-fullreport(8) result must contain exactly one report.")

    return fullreport["report"][0]

# ------------------------------------------------------------------------------

@dataclass
class CliArgs:
    vg: str
    pool_lv: str

    file: Optional[Path]
    verbose: bool

def _get_cli_args() -> CliArgs:
    parser = argparse.ArgumentParser(
        prog="lvm-thin-helper",
        description="Find the physical volumes that contain LVM2 thin-provisioned volumes.",
    )

    parser.add_argument("vg", help="Name of the LVM2 VG to check.")
    parser.add_argument("pool_lv", help="Name of the LVM2 LV that acts as the data pool.")

    parser.add_argument(
        "-f",
        "--file",
        help="Path to a json-formatted LVM2 fullreport file to use instead of live metadata. "
        "This file must only contain the report for a single VG. See lvm-fullreport(8) for more details.",
        type=Path
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging.",
        action="store_true",
        default=False
    )

    return CliArgs(**vars(parser.parse_args()))

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    args = _get_cli_args()
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # 1. Get the LVM2 fullreport for the target VG.
    report = _parse_fullreport(args.vg, args.file)

    # 2. Make sure we have the correct VG.
    vg_count = len(report["vg"])
    if vg_count != 1:
        raise ValueError(f"Expected 1 VG, got {vg_count}.")

    vg_name = report["vg"][0]["vg_name"]
    if vg_name != args.vg:
        raise ValueError(f"Expected VG named `{args.vg}`, got `{vg_name}`.")

    # 3. Get all LVs that have "thin" segment types.
    lvs_uuid_with_thin_segments = frozenset(seg["lv_uuid"] for seg in report["seg"] if seg["segtype"] == "thin")
    logger.debug("LVs with thin segments: %s", lvs_uuid_with_thin_segments)

    # 4. Get the UUIDs of the target pool LV.
    pool_lvs = [lv for lv in report["lv"] if lv["lv_name"] == args.pool_lv]

    if len(pool_lvs) != 1:
        raise ValueError(f"Expected 1 pool LV, got {len(pool_lvs)}.")

    pool_lv_uuid = pool_lvs[0]["lv_uuid"]
    logger.debug("Pool LV UUID: %s", pool_lv_uuid)

    pool_data_lv_uuid = pool_lvs[0]["data_lv_uuid"]
    logger.debug("Pool data LV UUID: %s", pool_data_lv_uuid)

    # 5. Get the thin-provisioned LVs part of the target pool LV.
    thin_provisioned_lvs_name = [
        lv["lv_name"] for lv in report["lv"]
        if lv["lv_uuid"] in lvs_uuid_with_thin_segments and lv["pool_lv_uuid"] == pool_lv_uuid
    ]

    logger.debug("Thin-provisioned LVs: %s", thin_provisioned_lvs_name)

    # 6. Get the PVs that have segments of the target pool LV.
    pvs_uuid_with_pool_lv_segments = frozenset(
        pvseg["pv_uuid"] for pvseg in report["pvseg"]
        if pvseg["lv_uuid"] == pool_data_lv_uuid
    )

    pv_name_by_uuid = {pv["pv_uuid"]: pv["pv_name"] for pv in report["pv"]}
    pvs_name_with_pool_lv_segments = [pv_name_by_uuid[pv_uuid] for pv_uuid in pvs_uuid_with_pool_lv_segments]

    logger.debug("PVs with segments of the pool LV: %s", pvs_name_with_pool_lv_segments)

    # 7. Profit!
    print(json.dumps({"pvs": pvs_name_with_pool_lv_segments, "lvs": thin_provisioned_lvs_name}))  # noqa: T201
