#!/usr/bin/env bash
#
# Check the commit message conventions of a pull request.
#
# Usage: check-commit-messages.sh <base-sha> <head-sha> <pr-number>
#
# Rules:
# - Format: `<type>(<scope>): <subject>`, with type in `feat`, `fix`, `docs` or `chore`.
# - `feat`, `fix` and `docs` require a scope. `chore` accepts an optional one.
# - A scope must be in the allowed list of `.github/commit-scopes.txt`.
# - The subject is at most 70 characters long, counting the ` (#<pr-number>)` suffix (already there
#   or added at merge). It is separated from the type/scope by exactly one space, starts with a
#   lowercase letter or a non-letter character, and does not end with a period.
# - If the commit has a body, the second line of the message must be blank.
# - A commit that only touches files in `tests/` must have a scope starting with `tests/`
#   (even for `chore`), and a scope starting with `tests/` is only allowed for such commits.
# - A `chore` commit touching files in `src/` or `tests/` only triggers a warning (never a failure).
# - If the pull request has several commits, each one should end with ` (#<pr-number>)`.
#   With a single commit nothing is checked: the ID is added when the pull request is merged.

set -euo pipefail

readonly SCOPES_FILE_PATH="$(dirname "$0")/../commit-scopes.txt"

readonly MAX_SUBJECT_LENGTH=70

# ==============================================================================

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <base-sha> <head-sha> <pr-number>" >&2
    exit 2
fi

readonly BASE_SHA=$1
readonly HEAD_SHA=$2
readonly PR_NUMBER=$3

# ------------------------------------------------------------------------------

report_error() {
    echo "::error::$1"
    errors=$((errors + 1))
}

report_warning() {
    echo "::warning::$1"
}

# ------------------------------------------------------------------------------

# Print the reason why a message (without PR ID) does not match `COMMIT_REGEX`.
get_format_error() {
    local message=$1
    if ! [[ $message =~ ^(feat|fix|docs|chore)($|[^[:alnum:]_-]) ]]; then
        echo "the type must be \`feat\`, \`fix\`, \`docs\` or \`chore\` "
    elif [[ $message =~ ^(feat|fix|docs)($|[^\(]) ]]; then
        echo "this type requires a scope, one of [${DISPLAYED_SCOPES%, }]"
    elif [[ $message =~ ^[a-z]+\( ]] && ! [[ $message =~ ^[a-z]+${SCOPE_REGEX} ]]; then
        echo "invalid scope, expected one of [${DISPLAYED_SCOPES%, }]"
    else
        echo "expected \`: \` (colon and one space) after the type or the scope, then a summary"
    fi
}

# ------------------------------------------------------------------------------

# Read the allowed scopes, one per line, ignoring comments and blank lines.
mapfile -t scopes < <(grep -vE '^[[:space:]]*(#|$)' "$SCOPES_FILE_PATH" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
if [ "${#scopes[@]}" -eq 0 ]; then
    report_error "No allowed scope found in \`${SCOPES_FILE_PATH}\`."
    exit 2
fi

# Escape the regex special characters of each scope, then join them with `|`.
ALLOWED_SCOPES=$(printf '%s\n' "${scopes[@]}" | sed -E 's/[][\\.^$*+?(){}|]/\\&/g' | paste -sd'|')
readonly ALLOWED_SCOPES

DISPLAYED_SCOPES=$(printf '`%s`, ' "${scopes[@]}")
readonly DISPLAYED_SCOPES

readonly PR_ID_SUFFIX=" (#${PR_NUMBER})"

readonly SUBJECT_REGEX='.*[^ ]'
readonly SCOPE_REGEX="\\((${ALLOWED_SCOPES})\\)"
readonly COMMIT_REGEX="^((feat|fix|docs)${SCOPE_REGEX}|chore(${SCOPE_REGEX})?): ${SUBJECT_REGEX}$"

# ------------------------------------------------------------------------------

mapfile -t hashes < <(git log --no-merges --format=%H "${BASE_SHA}..${HEAD_SHA}")

# ------------------------------------------------------------------------------

get_changed_files() {
    git diff-tree --root --no-commit-id --name-only -r "$1"
}

is_touching_only_tests() {
    local files
    files=$(get_changed_files "$1")
    [ -n "$files" ] && ! grep -qv '^tests/' <<< "$files"
}

is_touching_src_or_tests() {
    local files
    files=$(get_changed_files "$1")
    grep -qE '^(src|tests)/' <<< "$files"
}

# ------------------------------------------------------------------------------

errors=0
for hash in "${hashes[@]}"; do
    subject=$(git log -1 --format=%s "$hash")
    # The ID is optional here: the format is checked without it.
    message=${subject% (#[0-9]*)}

    if ! [[ $message =~ $COMMIT_REGEX ]]; then
        reason=$(get_format_error "$message")
        report_error "Invalid commit format, ${reason}: \"${subject}\"."
        continue
    fi

    subject_length=$((${#message} + ${#PR_ID_SUFFIX}))
    if [ "$subject_length" -gt "$MAX_SUBJECT_LENGTH" ]; then
        report_error "Commit subject must be at most ${MAX_SUBJECT_LENGTH} characters long including \`${PR_ID_SUFFIX}\`, got ${subject_length}: \"${subject}\"."
    fi

    summary=${message#*: }
    if [[ $summary == " "* ]]; then
        report_error "Commit subject must be separated from the type by exactly one space: \"${subject}\"."
    fi
    if [[ $summary =~ ^[[:upper:]] ]]; then
        report_error "Commit subject must not start with an uppercase letter: \"${subject}\"."
    fi
    if [[ $summary == *. ]]; then
        report_error "Commit subject must not end with a period: \"${subject}\"."
    fi

    scope=""
    if [[ $message =~ ^[a-z]+\(([^\)]+)\) ]]; then
        scope=${BASH_REMATCH[1]}
    fi
    if is_touching_only_tests "$hash"; then
        if [[ $scope != tests/* ]]; then
            report_error "Commit only touches \`tests/\`, its scope must start with \`tests/\`: \"${subject}\"."
        fi
    elif [[ $scope == tests/* ]]; then
        report_error "Scope \`${scope}\` is only allowed for commits that only touch \`tests/\`: \"${subject}\"."
    fi

    if [[ $message == chore* ]] && is_touching_src_or_tests "$hash"; then
        report_warning "Commit \`chore\` touches files in \`src/\` or \`tests/\`, consider \`feat\`, \`fix\` or \`docs\`: \"${subject}\"."
    fi

    if [ "${#hashes[@]}" -gt 1 ] && [[ $subject != *"$PR_ID_SUFFIX" ]]; then
        report_warning "Commit message must end with \"${PR_ID_SUFFIX}\": \"${subject}\"."
    fi

    second_line=$(git log -1 --format=%B "$hash" | sed -n 2p)
    if [ -n "$second_line" ]; then
        report_error "Commit message must have a blank line between the subject and the body: \"${subject}\"."
    fi
done

if [ "$errors" -ne 0 ]; then
    exit 1
fi
echo "${#hashes[@]} commit message(s) checked: OK."
