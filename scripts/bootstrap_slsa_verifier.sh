#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# bootstrap_slsa_verifier.sh — vendors the slsa-framework/slsa-verifier
# binary into KOSMOS_PLUGIN_VENDOR_ROOT (default ~/.kosmos/vendor) for
# the host's platform.
#
# Invoked automatically by `kosmos plugin install <name>` on first use
# when the platform-specific binary is missing (per Spec 1636 R-3 + the
# `binary_not_found` arm of kosmos.plugins.slsa.SLSAFailureKind). Can
# also be run manually to refresh the vendored binary.
#
# Usage:
#   scripts/bootstrap_slsa_verifier.sh [--version vX.Y.Z]
#
# Default version pinned via _DEFAULT_VERSION below; override with the
# --version flag if the upstream releases new builds. The download URL
# pattern matches the official slsa-framework/slsa-verifier releases.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_VERSION="v2.6.0"
_VENDOR_ROOT="${KOSMOS_PLUGIN_VENDOR_ROOT:-$HOME/.kosmos/vendor}"

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

version="$_DEFAULT_VERSION"
while (( "$#" )); do
  case "$1" in
    --version)
      shift
      version="$1"
      ;;
    -h|--help)
      grep '^#' "$0" | sed 's|^# \?||'
      exit 0
      ;;
    *)
      echo "unknown flag: $1" >&2
      exit 2
      ;;
  esac
  shift || true
done

# ---------------------------------------------------------------------------
# Detect platform
# ---------------------------------------------------------------------------

uname_s="$(uname -s)"
uname_m="$(uname -m)"

case "$uname_s" in
  Darwin) os="darwin" ;;
  Linux)  os="linux"  ;;
  *)
    echo "unsupported OS: $uname_s" >&2
    exit 1
    ;;
esac

case "$uname_m" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *)
    echo "unsupported architecture: $uname_m" >&2
    exit 1
    ;;
esac

platform_dir="${os}-${arch}"
target_dir="${_VENDOR_ROOT}/slsa-verifier/${platform_dir}"
target_bin="${target_dir}/slsa-verifier"

# ---------------------------------------------------------------------------
# Idempotent: skip if already vendored at the requested version
# ---------------------------------------------------------------------------

if [[ -x "$target_bin" ]]; then
  installed="$("$target_bin" --version 2>&1 | head -1 || true)"
  if echo "$installed" | grep -q "$version"; then
    echo "✓ slsa-verifier ${version} already vendored at ${target_bin}"
    exit 0
  fi
  echo "ℹ slsa-verifier present but version differs (got '${installed}'); re-downloading ${version}"
fi

# ---------------------------------------------------------------------------
# Download + verify checksum + install
# ---------------------------------------------------------------------------

# Upstream release assets follow the pattern:
#   slsa-verifier-${os}-${arch}
download_name="slsa-verifier-${os}-${arch}"
download_url="https://github.com/slsa-framework/slsa-verifier/releases/download/${version}/${download_name}"

mkdir -p "$target_dir"
tmp_file="$(mktemp -t slsa-verifier-XXXXXX)"
trap 'rm -f "$tmp_file"' EXIT

# C7 + Sec C-2 (review re-eval correction): pinned SHA-256 dictionary
# keyed by (version, os, arch). Source-of-truth: actual upstream
# artifact bytes verified on 2026-04-26 by downloading each binary +
# running `sha256sum`. Upstream releases do NOT ship a `.sha256`
# sidecar — only `.intoto.jsonl` provenance, which requires
# slsa-verifier itself to validate (the bootstrap chicken-and-egg).
# The pinned dictionary is therefore the only verification source
# available at bootstrap time.
#
# When pinning a new ${version}: download each platform binary
# manually and update the dictionary below. NEVER trust unverified
# bytes — a hash mismatch is fail-closed.
declare -A EXPECTED_SHA256
EXPECTED_SHA256["v2.6.0|darwin|amd64"]="f838adf01bbe62b883e7967167fa827bbf7373f83e2d7727ec18e53f725fee93"
EXPECTED_SHA256["v2.6.0|darwin|arm64"]="8740e66832fd48bbaa479acd5310986b876ff545460add0cb4a087aec056189c"
EXPECTED_SHA256["v2.6.0|linux|amd64"]="1c9c0d6a272063f3def6d233fa3372adbaff1f5a3480611a07c744e73246b62d"
EXPECTED_SHA256["v2.6.0|linux|arm64"]="92b28eb2db998f9a6a048336928b29a38cb100076cd587e443ca0a2543d7c93d"

key="${version}|${os}|${arch}"
pinned="${EXPECTED_SHA256[$key]:-}"

if [[ -z "$pinned" ]]; then
  echo "⛔ no pinned SHA-256 for '${key}' — refusing to install unverified binary." >&2
  echo "   Manually verify https://github.com/slsa-framework/slsa-verifier/releases/tag/${version}" >&2
  echo "   and add a row to EXPECTED_SHA256 in bootstrap_slsa_verifier.sh." >&2
  exit 1
fi

echo "📥 downloading ${download_url}"
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 --retry-delay 2 --proto '=https' --tlsv1.2 \
    -o "$tmp_file" "$download_url"
elif command -v wget >/dev/null 2>&1; then
  wget --secure-protocol=TLSv1_2 -O "$tmp_file" "$download_url"
else
  echo "neither curl nor wget is available; install one and retry" >&2
  exit 1
fi

# Compute actual SHA-256 and compare to pinned.
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$tmp_file" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  actual="$(shasum -a 256 "$tmp_file" | awk '{print $1}')"
else
  echo "neither sha256sum nor shasum available; install one and retry" >&2
  exit 1
fi

if [[ "$actual" != "$pinned" ]]; then
  echo "⛔ SHA-256 mismatch — refusing to install:" >&2
  echo "   key:      ${key}" >&2
  echo "   expected: ${pinned}" >&2
  echo "   actual:   ${actual}" >&2
  echo "" >&2
  echo "   This means the downloaded binary does not match the byte-exact" >&2
  echo "   value the bootstrap script was pinned to. Either:" >&2
  echo "   (a) the upstream release was tampered with — DO NOT use this binary;" >&2
  echo "   (b) the pinned hash is stale — verify the new release manually" >&2
  echo "       and update EXPECTED_SHA256 in bootstrap_slsa_verifier.sh." >&2
  exit 1
fi
verifier_msg="pinned SHA-256 dict"

# Move into place + chmod +x.
mv "$tmp_file" "$target_bin"
chmod +x "$target_bin"

echo "✓ vendored slsa-verifier ${version} → ${target_bin}"
echo "  SHA-256 verified via ${verifier_msg}"

# Sanity-check: --version flag should work.
if "$target_bin" --version >/dev/null 2>&1; then
  echo "  $("$target_bin" --version 2>&1 | head -1)"
else
  echo "⚠ binary downloaded but --version failed; manual verification recommended" >&2
fi
