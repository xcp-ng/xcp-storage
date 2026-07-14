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

set(STAMP_NAME "build.stamp")
set(STAMP_FILE "${CMAKE_CURRENT_BINARY_DIR}/${STAMP_NAME}")

# ------------------------------------------------------------------------------

set(PLUGINS_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/plugins")

file(GLOB_RECURSE PLUGIN_SOURCE_LIST
    CONFIGURE_DEPENDS
    "${PLUGINS_DIR}/*.py"
)

set_property(DIRECTORY APPEND PROPERTY
    CMAKE_CONFIGURE_DEPENDS "${PLUGINS_DIR}"
)

add_custom_command(
    OUTPUT ${STAMP_FILE}
    COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/build.py" "${PLUGINS_OUTPUT_DIR}"
    COMMAND ${CMAKE_COMMAND} -E touch ${STAMP_FILE}
    DEPENDS ${PLUGIN_SOURCE_LIST} "${CMAKE_CURRENT_SOURCE_DIR}/build.py"
    COMMENT "Generating SMAPIv3 plugins..."
)
add_custom_target(${CONNECTOR_NAME} ALL DEPENDS ${STAMP_FILE})

# ------------------------------------------------------------------------------

install(DIRECTORY "${PLUGINS_OUTPUT_DIR}/"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR}/xapi-storage-script
    USE_SOURCE_PERMISSIONS
)
