#!/usr/bin/env bash
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

# ==============================================================================
# Helpers to handle the pull request ID (` (#<number>)`) at the end of a commit title.
# ==============================================================================

# Matches one pull request ID, with its leading space, at the end of a title.
readonly PR_ID_REGEX=' \(#[0-9]+\)$'

# Succeed if the argument is a valid pull request number.
is_pr_number() {
    [[ $1 =~ ^[0-9]+$ ]]
}

# Print the suffix to add to a commit title for the given pull request number.
get_pr_id_suffix() {
    echo " (#$1)"
}

# True if a commit title ends with a pull request ID.
has_pr_id() {
    [[ $1 =~ $PR_ID_REGEX ]]
}

# Print a commit title without its last pull request ID, if any.
strip_pr_id() {
    local subject=$1
    if [[ $subject =~ $PR_ID_REGEX ]]; then
        subject=${subject%"${BASH_REMATCH[0]}"}
    fi
    echo "$subject"
}

# Print a commit title without its trailing pull request IDs.
strip_pr_ids() {
    local subject=$1
    while has_pr_id "$subject"; do
        subject=$(strip_pr_id "$subject")
    done
    echo "$subject"
}

# Print a commit title with its trailing pull request IDs replaced by the given suffix.
with_pr_id() {
    local subject=$1
    local pr_id_suffix=$2
    echo "$(strip_pr_ids "$subject")${pr_id_suffix}"
}
