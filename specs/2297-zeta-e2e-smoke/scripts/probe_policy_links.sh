#!/usr/bin/env bash
# probe_policy_links.sh — Epic ζ T022 / SC-009
#
# Extract HTTP/HTTPS URLs from docs/research/policy-mapping.md, probe each via
# `curl -I --max-time 5 -L -o /dev/null -w "%{http_code}"`, and exit 0 iff all
# return 2xx/3xx. Used by SC-009 verification + by Lead during T021 authoring.
#
# Usage: bash specs/2297-zeta-e2e-smoke/scripts/probe_policy_links.sh
#
# Exit codes:
#   0 — all URLs reachable (2xx/3xx)
#   1 — one or more URLs failed
#   2 — doc not found / curl missing

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${HERE}/../../.." && pwd)"
DOC="${REPO_ROOT}/docs/research/policy-mapping.md"

if [[ ! -f "$DOC" ]]; then
  echo "FATAL: ${DOC} not found" >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "FATAL: curl not on PATH" >&2
  exit 2
fi

# Extract HTTP(S) URLs. Match-stop on whitespace, ), ], or trailing punctuation.
# Strip trailing comma / period / closing-paren defensively.
# Portable across bash 3.2 (macOS) and 4+ (Linux) — no mapfile.
URL_LIST=$(
  grep -oE 'https?://[A-Za-z0-9._~:/?#@!$&'"'"'()*+,;=%-]+' "$DOC" \
    | sed -E 's/[.,;:)]+$//' \
    | sort -u
)

URL_COUNT=$(printf "%s\n" "$URL_LIST" | grep -c '^https' || true)

if [[ ${URL_COUNT} -eq 0 ]]; then
  echo "FATAL: no URLs extracted from ${DOC}" >&2
  exit 2
fi

echo "Probing ${URL_COUNT} URLs from ${DOC} ..."

FAIL=0
PASS=0
FAILED_URLS=""

while IFS= read -r url; do
  [[ -z "$url" ]] && continue
  # GET-only probe — HEAD is unreliable across redirects on KR/JP/SG sites.
  # Single curl call with -L follows redirects; %{http_code} = final code.
  # User-Agent helps with sites that block default curl UA (Singpass etc.).
  # Trust curl's %{http_code} — it writes "000" on connection failure
  # naturally; appending an OR-fallback would concatenate codes when curl
  # exits non-zero (e.g. exit 47 on redirect-loop) but %{http_code} is set.
  code=$(curl -s -L --max-time 7 --max-redirs 10 -A "KOSMOS-link-probe/1.0" \
    -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
  [[ -z "$code" ]] && code="000"
  if [[ "$code" =~ ^[23][0-9]{2}$ ]]; then
    PASS=$((PASS + 1))
    printf "  [PASS %s] %s\n" "$code" "$url"
  else
    FAIL=$((FAIL + 1))
    FAILED_URLS="${FAILED_URLS}${code} ${url}"$'\n'
    printf "  [FAIL %s] %s\n" "$code" "$url" >&2
  fi
done <<< "$URL_LIST"

echo ""
echo "=== Summary ==="
echo "PASS: ${PASS} / ${URL_COUNT}"
echo "FAIL: ${FAIL} / ${URL_COUNT}"

if [[ $FAIL -gt 0 ]]; then
  echo ""
  echo "Failed URLs:" >&2
  printf "%s" "$FAILED_URLS" >&2
  exit 1
fi

exit 0
