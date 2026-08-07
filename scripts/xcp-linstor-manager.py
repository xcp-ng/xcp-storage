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

from xcp_storage.backends.linstor.manager import LinstorManager

# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--uri", required=False)

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--remove-skip-disks", action="store_true")

    args = parser.parse_args()

    linstor_manager = LinstorManager(args.uri)
    if args.remove_skip_disks:
        linstor_manager.remove_controller_skip_disks()
