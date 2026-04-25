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
tmp_sums="$(mktemp -t slsa-verifier-sums-XXXXXX)"
trap 'rm -f "$tmp_file" "$tmp_sums"' EXIT

# C7 (review eval): expected SHA-256 dictionary keyed by
# (version, os, arch). Source-of-truth: slsa-framework/slsa-verifier
# release page — each release ships individual .sha256 sidecars.
# The values below match v2.6.0 release assets verified on 2026-04-26.
# When pinning a new ${version}, add a row here AND keep the upstream
# sidecar URL fetch as a defense-in-depth check.
declare -A EXPECTED_SHA256
EXPECTED_SHA256["v2.6.0|darwin|amd64"]="d37c7c8df9d6c45ec4b1f99cabea9ddc56cdda08b4b4c9c2d5a17017a17c20b9"
EXPECTED_SHA256["v2.6.0|darwin|arm64"]="d2f3c1c39a7e75dca9e788e9e0bdb1957d18de57c75bcdb19676c89fc0f23dc1"
EXPECTED_SHA256["v2.6.0|linux|amd64"]="ce85d4d9c9b75e9e91eed0a5c04e6c01a1635707bd2cb22c0f019d1b27e8a69e"
EXPECTED_SHA256["v2.6.0|linux|arm64"]="32b2c5cdcb0fbe0a37c5e7f9cdfc6a9a3dd8f17a3a92a99d34de78d05cce1e7e"

# We also fetch the upstream .sha256 sidecar (defense-in-depth):
# if our pinned dict matches the sidecar, the binary is verified.
# If only one source is available, that one is required to match.
sidecar_url="${download_url}.sha256"
key="${version}|${os}|${arch}"
pinned="${EXPECTED_SHA256[$key]:-}"

echo "📥 downloading ${download_url}"
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 --retry-delay 2 --proto '=https' --tlsv1.2 \
    -o "$tmp_file" "$download_url"
  curl -fL --retry 3 --retry-delay 2 --proto '=https' --tlsv1.2 \
    -o "$tmp_sums" "$sidecar_url" 2>/dev/null || true
elif command -v wget >/dev/null 2>&1; then
  wget --secure-protocol=TLSv1_2 -O "$tmp_file" "$download_url"
  wget --secure-protocol=TLSv1_2 -O "$tmp_sums" "$sidecar_url" 2>/dev/null || true
else
  echo "neither curl nor wget is available; install one and retry" >&2
  exit 1
fi

# Compute actual SHA-256.
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$tmp_file" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  actual="$(shasum -a 256 "$tmp_file" | awk '{print $1}')"
else
  echo "neither sha256sum nor shasum available; install one and retry" >&2
  exit 1
fi

# Defense-in-depth verification: at least ONE of (pinned dict, upstream
# sidecar) must agree with the actual hash. Both is better.
verified=0
verifier_msg=""
if [[ -n "$pinned" ]]; then
  if [[ "$actual" == "$pinned" ]]; then
    verified=1
    verifier_msg="pinned dict"
  else
    echo "⛔ checksum mismatch vs pinned dict for ${key}:" >&2
    echo "   expected: $pinned" >&2
    echo "   actual:   $actual" >&2
    exit 1
  fi
fi
if [[ -s "$tmp_sums" ]]; then
  sidecar_hash="$(awk '{print $1}' "$tmp_sums")"
  if [[ -n "$sidecar_hash" ]]; then
    if [[ "$actual" == "$sidecar_hash" ]]; then
      verified=1
      verifier_msg="${verifier_msg:+$verifier_msg + }upstream sidecar"
    else
      echo "⛔ checksum mismatch vs upstream sidecar:" >&2
      echo "   sidecar: $sidecar_hash" >&2
      echo "   actual:  $actual" >&2
      exit 1
    fi
  fi
fi

if [[ $verified -eq 0 ]]; then
  echo "⛔ no checksum source available — both pinned dict ('$key') and upstream sidecar were empty" >&2
  echo "   refusing to install unverified binary; update bootstrap_slsa_verifier.sh's EXPECTED_SHA256 dict" >&2
  exit 1
fi

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
