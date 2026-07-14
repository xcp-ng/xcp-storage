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

# ==============================================================================

set(CONNECTOR_NAME "SMAPIv3")

set(PLUGINS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/plugins")

# ------------------------------------------------------------------------------

set(STAMP_FILE "${CMAKE_CURRENT_BINARY_DIR}/build.stamp")

# ------------------------------------------------------------------------------

set(PLUGINS_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/plugins")

file(GLOB_RECURSE PLUGIN_SOURCE_LIST
    CONFIGURE_DEPENDS
    "${PLUGINS_DIR}/*.py"
)

set(PLUGIN_LIST_FILE "${CMAKE_CURRENT_BINARY_DIR}/plugins.list")
string(REPLACE ";" "\n" PLUGIN_LIST_CONTENT "${PLUGIN_SOURCE_LIST}")
file(CONFIGURE
    OUTPUT "${PLUGIN_LIST_FILE}"
    CONTENT "${PLUGIN_LIST_CONTENT}\n"
    @ONLY
)

add_custom_command(
    OUTPUT "${STAMP_FILE}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/build.py" "${PLUGINS_OUTPUT_DIR}"
    COMMAND "${CMAKE_COMMAND}" -E touch "${STAMP_FILE}"
    DEPENDS ${PLUGIN_SOURCE_LIST} "${PLUGIN_LIST_FILE}" "${CMAKE_CURRENT_SOURCE_DIR}/build.py"
    COMMENT "Generating SMAPIv3 plugins..."
    VERBATIM
)
add_custom_target(${CONNECTOR_NAME} ALL DEPENDS "${STAMP_FILE}")

# ------------------------------------------------------------------------------

install(DIRECTORY "${PLUGINS_OUTPUT_DIR}/"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR}/xapi-storage-script
    USE_SOURCE_PERMISSIONS
)
