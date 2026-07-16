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

cmake_minimum_required(VERSION 3.26.4)

# ==============================================================================

project(xcp-storage VERSION 1.0.0 LANGUAGES C)

include(GNUInstallDirs)

# ------------------------------------------------------------------------------
# Dependencies.
# ------------------------------------------------------------------------------

find_package(PkgConfig REQUIRED)
if (NOT DEFINED SYSTEMD_SYSTEM_UNIT_DIR)
    pkg_get_variable(SYSTEMD_SYSTEM_UNIT_DIR systemd systemdsystemunitdir)
endif()

# ------------------------------------------------------------------------------
# Daemons.
# ------------------------------------------------------------------------------

set(DAEMON_LIST
    "xcp-storage-rpc"
)

foreach(DAEMON IN LISTS DAEMON_LIST)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/daemons/${DAEMON})
endforeach()
