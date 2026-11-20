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

install(PROGRAMS ${CMAKE_CURRENT_SOURCE_DIR}/xcp-storage-pool-hosts.py
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR}/${PROJECT_NAME}
    RENAME xcp-storage-pool-hosts
    PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                GROUP_READ GROUP_EXECUTE
                WORLD_READ WORLD_EXECUTE
)

configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/xcp-storage-pool-hosts.service.in
    ${CMAKE_CURRENT_BINARY_DIR}/xcp-storage-pool-hosts.service
    @ONLY
)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/xcp-storage-pool-hosts.service
    DESTINATION ${SYSTEMD_SYSTEM_UNIT_DIR}
    PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
)
