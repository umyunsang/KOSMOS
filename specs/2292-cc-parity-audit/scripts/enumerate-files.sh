#!/usr/bin/env bash
# T003 — R1 file enumeration.
# Produces 5 deterministic file lists under data/:
#   enumerated-keep-byte-identical.txt   (UMMAYA == CC, byte-for-byte)
#   enumerated-import-candidate.txt      (Files differ — candidates for SDK-import-only-diff verification)
#   enumerated-modified.txt              (Files differ — full union; superset of import-candidate before R3 verification)
#   enumerated-ummaya-only.txt           (UMMAYA-only ADDITIONS)
#   enumerated-cc-only.txt               (CC-only DELETE — already removed from UMMAYA)
#
# Read-only: writes only inside specs/2292-cc-parity-audit/data/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

cd "$UMMAYA_ROOT"

UMMAYA_REL=$(realpath --relative-to="$UMMAYA_ROOT" "$UMMAYA_DIR" 2>/dev/null || python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$UMMAYA_DIR" "$UMMAYA_ROOT")
CC_REL=$(realpath --relative-to="$UMMAYA_ROOT" "$CC_DIR" 2>/dev/null || python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$CC_DIR" "$UMMAYA_ROOT")

echo "[R1] enumerate UMMAYA file set ($UMMAYA_REL)..."
( cd "$UMMAYA_DIR" && find . -type f \( -name '*.ts' -o -name '*.tsx' \) | sed 's|^\./||' | sort > "$DATA_DIR/.tmp-ummaya.txt" )

echo "[R1] enumerate CC file set ($CC_REL)..."
( cd "$CC_DIR" && find . -type f \( -name '*.ts' -o -name '*.tsx' \) | sed 's|^\./||' | sort > "$DATA_DIR/.tmp-cc.txt" )

echo "[R1] compute set differences..."
# UMMAYA-only (in UMMAYA, not in CC) → ADDITIONS
comm -23 "$DATA_DIR/.tmp-ummaya.txt" "$DATA_DIR/.tmp-cc.txt" | \
  awk -v p="$UMMAYA_REL" '{print p"/"$0}' > "$DATA_DIR/enumerated-ummaya-only.txt"

# CC-only (in CC, not in UMMAYA) → DELETE
comm -13 "$DATA_DIR/.tmp-ummaya.txt" "$DATA_DIR/.tmp-cc.txt" | \
  awk -v p="$CC_REL" '{print p"/"$0}' > "$DATA_DIR/enumerated-cc-only.txt"

# Both: split into byte-identical vs differing
echo "[R1] hash compare both-side files..."
comm -12 "$DATA_DIR/.tmp-ummaya.txt" "$DATA_DIR/.tmp-cc.txt" > "$DATA_DIR/.tmp-both.txt"

: > "$DATA_DIR/enumerated-keep-byte-identical.txt"
: > "$DATA_DIR/enumerated-modified.txt"

# Hash compare. Use shasum -a 256 if sha256sum unavailable (macOS).
HASH_CMD="sha256sum"
if ! command -v sha256sum >/dev/null 2>&1; then
  HASH_CMD="shasum -a 256"
fi

while IFS= read -r relpath; do
  [[ -z "$relpath" ]] && continue
  k_hash=$($HASH_CMD "$UMMAYA_DIR/$relpath" 2>/dev/null | awk '{print $1}')
  c_hash=$($HASH_CMD "$CC_DIR/$relpath" 2>/dev/null | awk '{print $1}')
  if [[ "$k_hash" == "$c_hash" && -n "$k_hash" ]]; then
    echo "$UMMAYA_REL/$relpath" >> "$DATA_DIR/enumerated-keep-byte-identical.txt"
  else
    echo "$UMMAYA_REL/$relpath" >> "$DATA_DIR/enumerated-modified.txt"
  fi
done < "$DATA_DIR/.tmp-both.txt"

# Sort all outputs deterministically.
for f in "$DATA_DIR"/enumerated-*.txt; do
  sort -o "$f" "$f"
done

# Derive import-candidate list: subset of all-differing files whose diff
# touches only `import|from|export` lines. Heuristic for cc-source-scope-audit § 1.1
# baseline (73 candidates). The full verification happens in R3 (T013/T014).
echo "[R1] derive import-candidate subset (heuristic)..."
: > "$DATA_DIR/enumerated-import-candidate.txt"
IMPORT_RE='^[+-][[:space:]]*(import|from|export[[:space:]]+\*[[:space:]]+from|export[[:space:]]*\{[^}]*\}[[:space:]]*from)\b'
while IFS= read -r relpath_with_prefix; do
  relpath="${relpath_with_prefix#$UMMAYA_REL/}"
  diff_out=$(diff -u "$CC_DIR/$relpath" "$UMMAYA_DIR/$relpath" 2>/dev/null | tail -n +3 || true)
  # Drop the leading +++/--- header lines, then check whether every +/- line is an import line.
  body_diff=$(echo "$diff_out" | grep -E '^[+-]' | grep -vE "$IMPORT_RE" || true)
  if [[ -z "$body_diff" ]]; then
    echo "$relpath_with_prefix" >> "$DATA_DIR/enumerated-import-candidate.txt"
  fi
done < "$DATA_DIR/enumerated-modified.txt"
sort -o "$DATA_DIR/enumerated-import-candidate.txt" "$DATA_DIR/enumerated-import-candidate.txt"

# Subtract import-candidate from modified, leaving "strictly-modified" (i.e., body diff present).
# Preserves spec.md FR-001 contract: modified == files needing 3-class classification (not import-only).
comm -23 "$DATA_DIR/enumerated-modified.txt" "$DATA_DIR/enumerated-import-candidate.txt" \
  > "$DATA_DIR/.tmp-strict.txt"
mv "$DATA_DIR/.tmp-strict.txt" "$DATA_DIR/enumerated-modified.txt"

# Cleanup tmp.
rm -f "$DATA_DIR/.tmp-ummaya.txt" "$DATA_DIR/.tmp-cc.txt" "$DATA_DIR/.tmp-both.txt"

echo "[R1] done. Row counts:"
for f in keep-byte-identical import-candidate modified ummaya-only cc-only; do
  cnt=$(wc -l < "$DATA_DIR/enumerated-$f.txt" | tr -d ' ')
  printf "  %-22s %s\n" "$f" "$cnt"
done
