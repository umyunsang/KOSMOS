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

# Move into place + chmod +x.
mv "$tmp_file" "$target_bin"
chmod +x "$target_bin"

echo "✓ vendored slsa-verifier ${version} → ${target_bin}"

# Sanity-check: --version flag should work.
if "$target_bin" --version >/dev/null 2>&1; then
  echo "  $("$target_bin" --version 2>&1 | head -1)"
else
  echo "⚠ binary downloaded but --version failed; manual verification recommended" >&2
fi
