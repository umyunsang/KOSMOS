#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Purpose: Block re-introduction of long-lived GitHub Encrypted Secrets into
# in-scope workflow files; exits non-zero if any forbidden pattern is found.

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
_REPO_ROOT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-root)
            _REPO_ROOT="$2"
            shift 2
            ;;
        --repo-root=*)
            _REPO_ROOT="${1#--repo-root=}"
            shift
            ;;
        *)
            echo "audit-secrets: usage error — unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Repo-root detection — cd to the worktree root so relative paths work.
# ---------------------------------------------------------------------------
if [[ -z "${_REPO_ROOT}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    _REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
fi
cd "${_REPO_ROOT}"

# ---------------------------------------------------------------------------
# Scan scope — ONLY these files.  Epic #467 owns docker.yml / shadow-eval.yml /
# build-manifest.yml; touching them is a hard violation.
# ---------------------------------------------------------------------------
_SCANNED_FILES=(".github/workflows/ci.yml")

# ---------------------------------------------------------------------------
# Forbidden patterns (denylist) — from contracts/audit-secrets.md §Forbidden patterns
# Patterns match BOTH dot-notation (secrets.NAME) and bracket-notation
# (secrets['NAME'] / secrets["NAME"]) because GitHub accepts both. Grep runs
# case-insensitively (-i) because GitHub secret names are case-insensitive
# when referenced.
# ---------------------------------------------------------------------------
# 1. Any *_TOKEN secret reference
PATTERN_TOKEN='\$\{\{ *secrets[.[][^}]*_TOKEN[^}]*\}\}'
# 2. Any *_API_KEY secret reference
PATTERN_API_KEY='\$\{\{ *secrets[.[][^}]*_API_KEY[^}]*\}\}'
# 3. Any *_SECRET secret reference
PATTERN_SECRET='\$\{\{ *secrets[.[][^}]*_SECRET[^}]*\}\}'
# 4. Any KOSMOS_* secret reference (long-lived by definition)
PATTERN_KOSMOS='\$\{\{ *secrets[.[][^}]*KOSMOS_[^}]*\}\}'
# 5. Legacy FRIENDLI_* token references
PATTERN_FRIENDLI='\$\{\{ *secrets[.[][^}]*FRIENDLI[^}]*\}\}'
# 6. Langfuse secrets (must come via Infisical, not GH Secrets)
PATTERN_LANGFUSE='\$\{\{ *secrets[.[][^}]*LANGFUSE_[^}]*\}\}'

# Allowlisted literal strings (skip violation for these)
# - ${{ secrets.GITHUB_TOKEN }}  — GitHub-issued, short-lived
ALLOW_GITHUB_TOKEN='secrets[.[][^}]*GITHUB_TOKEN'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_violations=0
_violation_lines=""

# Check whether a line is on the allowlist.
# Returns 0 (true / skip) if the line should be suppressed.
_is_allowed() {
    local line="$1"

    # Suppress YAML block comments
    if echo "${line}" | grep -qE '^\s*#'; then
        return 0
    fi

    # Suppress uses: action-reference lines
    if echo "${line}" | grep -qE '^\s*uses:'; then
        return 0
    fi

    # Suppress ${{ secrets.GITHUB_TOKEN }} — short-lived, GitHub-managed.
    # Allow only when GITHUB_TOKEN is the sole secrets.* reference on the line.
    # Grep is case-insensitive; covers both dot and bracket notation.
    if echo "${line}" | grep -iqE "${ALLOW_GITHUB_TOKEN}"; then
        # Count total secrets references; if only GITHUB_TOKEN, suppress.
        local total_refs github_refs
        total_refs="$(echo "${line}"  | grep -ioE '\$\{\{ *secrets[.[][^}]*\}\}' | wc -l)"
        github_refs="$(echo "${line}" | grep -ioE '\$\{\{ *secrets[.[][^}]*GITHUB_TOKEN[^}]*\}\}' | wc -l)"
        if [[ "${total_refs}" -eq "${github_refs}" ]]; then
            return 0
        fi
    fi

    return 1
}

# Emit a violation record (to stderr) and accumulate it for sorted output.
_check_pattern() {
    local file="$1"
    local rule_id="$2"
    local pattern="$3"

    local lineno=0
    # `|| [[ -n "${line}" ]]` ensures we still process the final line when the
    # file has no trailing newline — otherwise a forbidden secret on EOF would
    # silently bypass the gate.
    while IFS= read -r line || [[ -n "${line}" ]]; do
        lineno=$(( lineno + 1 ))
        if echo "${line}" | grep -iqE "${pattern}"; then
            if ! _is_allowed "${line}"; then
                local snippet
                snippet="$(echo "${line}" | grep -ioE "${pattern}" | head -1)"
                _violation_lines="${_violation_lines}${file}:${lineno}:1:${rule_id}:${snippet}"$'\n'
                _violations=$(( _violations + 1 ))
            fi
        fi
    done < "${file}"
}

# ---------------------------------------------------------------------------
# Main scan loop
# ---------------------------------------------------------------------------
for _file in "${_SCANNED_FILES[@]}"; do
    if [[ ! -f "${_file}" ]]; then
        echo "audit-secrets: ERROR — scanned file not found: ${_file}" >&2
        exit 2
    fi
    if [[ ! -r "${_file}" ]]; then
        echo "audit-secrets: ERROR — scanned file unreadable: ${_file}" >&2
        exit 2
    fi

    _check_pattern "${_file}" "DENY-TOKEN"    "${PATTERN_TOKEN}"
    _check_pattern "${_file}" "DENY-API_KEY"  "${PATTERN_API_KEY}"
    _check_pattern "${_file}" "DENY-SECRET"   "${PATTERN_SECRET}"
    _check_pattern "${_file}" "DENY-KOSMOS"   "${PATTERN_KOSMOS}"
    _check_pattern "${_file}" "DENY-FRIENDLI" "${PATTERN_FRIENDLI}"
    _check_pattern "${_file}" "DENY-LANGFUSE" "${PATTERN_LANGFUSE}"
done

# ---------------------------------------------------------------------------
# Output: sort violations by (file, line_number) and print to stderr
# ---------------------------------------------------------------------------
if [[ ${_violations} -gt 0 ]]; then
    # Sort by file then by numeric line number (field 2, colon-delimited)
    _sorted="$(echo "${_violation_lines}" | grep -v '^$' | sort -t: -k1,1 -k2,2n)"

    while IFS= read -r entry; do
        [[ -z "${entry}" ]] && continue
        _vfile="$(echo "${entry}"   | cut -d: -f1)"
        _vline="$(echo "${entry}"   | cut -d: -f2)"
        _vrule="$(echo "${entry}"   | cut -d: -f4)"
        _vsnip="$(echo "${entry}"   | cut -d: -f5-)"
        {
            echo "audit-secrets: FORBIDDEN pattern in ${_vfile}:${_vline}:"
            echo "  ${_vsnip}"
            printf "  \342\206\222 Long-lived GH Encrypted Secret (%s). Move to Infisical + OIDC.\n" "${_vrule}"
            echo "    See docs/configuration.md#infisical-migration"
        } >&2
    done <<< "${_sorted}"

    echo "audit-secrets: ${_violations} violation(s) found." >&2
    exit 1
fi

echo "audit-secrets: clean — no forbidden patterns found." >&2
exit 0
