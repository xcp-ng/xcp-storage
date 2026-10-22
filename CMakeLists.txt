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

file(STRINGS ${CMAKE_CURRENT_SOURCE_DIR}/setup.cfg XCP_STORAGE_VERSION_LINE REGEX "^version *=")
string(REGEX REPLACE "^version *= *" "" XCP_STORAGE_VERSION "${XCP_STORAGE_VERSION_LINE}")
if (NOT XCP_STORAGE_VERSION)
    message(FATAL_ERROR "Unable to read the project version from setup.cfg.")
endif()

project(xcp-storage VERSION ${XCP_STORAGE_VERSION} LANGUAGES C)

# ------------------------------------------------------------------------------

include(GNUInstallDirs)

# ------------------------------------------------------------------------------
# Dependencies.
# ------------------------------------------------------------------------------

find_package(PkgConfig REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
if (NOT DEFINED SYSTEMD_SYSTEM_UNIT_DIR)
    pkg_get_variable(SYSTEMD_SYSTEM_UNIT_DIR systemd systemdsystemunitdir)
endif()

# ------------------------------------------------------------------------------
# Build info: generate `xcp_storage/build_info.py` in the source tree, so that
# it is part of the Python package.
# ------------------------------------------------------------------------------

set(XCP_STORAGE_GIT_COMMIT "unknown")
find_package(Git QUIET)
if (GIT_FOUND)
    execute_process(
        COMMAND ${GIT_EXECUTABLE} describe --always --dirty --abbrev=12
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        OUTPUT_VARIABLE GIT_DESCRIBE_OUTPUT
        RESULT_VARIABLE GIT_DESCRIBE_RESULT
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if (GIT_DESCRIBE_RESULT EQUAL 0)
        set(XCP_STORAGE_GIT_COMMIT "${GIT_DESCRIBE_OUTPUT}")
    endif()
endif()

string(TIMESTAMP XCP_STORAGE_BUILD_DATE "%Y-%m-%dT%H:%M:%SZ" UTC)

configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/xcp_storage/build_info.py.in
    ${CMAKE_CURRENT_SOURCE_DIR}/src/xcp_storage/build_info.py
    @ONLY
)

# ------------------------------------------------------------------------------
# Daemons.
# ------------------------------------------------------------------------------

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

add_compile_options(
    -Wall
    -Wcast-align
    -Wconversion
    -Wextra
    -Wfloat-equal
    -Winit-self
    -Wlogical-op
    -Wpointer-arith
    -Wreturn-type
    -Wsign-conversion
    -Wundef
    -Wuninitialized
    -Wunused
    -Wunused-const-variable
)

set(DAEMON_LIST
    "xcp-storage-fifo-lock"
    "xcp-storage-rpc"
)

foreach(DAEMON IN LISTS DAEMON_LIST)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/daemons/${DAEMON})
endforeach()

# ------------------------------------------------------------------------------
# Connectors.
# ------------------------------------------------------------------------------

set(CONNECTOR_LIST
    "smapi_v3"
)

foreach(CONNECTOR IN LISTS CONNECTOR_LIST)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/connectors/${CONNECTOR})
endforeach()
