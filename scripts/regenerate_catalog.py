#!/usr/bin/env -S uv run python
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the kosmos-plugin-store/index/index.json catalog.

Walks every `kosmos-plugin-store/kosmos-plugin-<name>` repo via the
`gh` CLI, collects published releases (or the main branch tarball when
no release exists yet), parses each repo's `manifest.yaml` for tier /
permission_layer / processes_pii / trustee_org_name, and emits a
fresh `index.json` per
``specs/1636-plugin-dx-5tier/contracts/catalog-index.schema.json``.

Usage::

    uv run python scripts/regenerate_catalog.py            # write to stdout
    uv run python scripts/regenerate_catalog.py --out PATH # write to file
    uv run python scripts/regenerate_catalog.py --check    # CI drift gate

Inputs come exclusively from `gh` CLI output (no auth tokens hard-coded).
The script trusts the `gh` CLI's auth context; install via
``brew install gh`` and ``gh auth login``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

ORG = "kosmos-plugin-store"
META_REPO = "index"
PLUGIN_PREFIX = "kosmos-plugin-"


def _run_gh(args: list[str], *, timeout: float = 30.0) -> str:
    """Invoke `gh` and return stdout. Raises on non-zero exit."""
    completed = subprocess.run(  # noqa: S603 — argv list, no shell.
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.stdout


def _list_plugin_repos() -> list[str]:
    """List every `kosmos-plugin-<name>` repo under the org (excludes index + template)."""
    raw = _run_gh(["repo", "list", ORG, "--json", "name", "--limit", "200"])
    repos = json.loads(raw)
    names: list[str] = []
    for r in repos:
        name = r.get("name", "")
        if not name.startswith(PLUGIN_PREFIX):
            continue
        if name == f"{PLUGIN_PREFIX}template":
            continue
        names.append(name)
    return sorted(names)


def _fetch_manifest(repo_name: str) -> dict[str, object] | None:
    """Pull `manifest.yaml` from the repo's main branch via gh api."""
    try:
        raw = _run_gh(
            [
                "api",
                f"repos/{ORG}/{repo_name}/contents/manifest.yaml",
                "--jq",
                ".content",
            ]
        ).strip()
    except subprocess.CalledProcessError:
        return None
    if not raw:
        return None
    import base64

    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        loaded = yaml.safe_load(decoded)
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def _bundle_sha(repo_name: str) -> str | None:
    """Compute SHA-256 of the main-branch tarball — same shape `kosmos plugin install` will see."""
    import hashlib

    url = f"https://github.com/{ORG}/{repo_name}/archive/refs/heads/main.tar.gz"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 — fixed github URL.
            data = resp.read()
    except Exception:
        return None
    return hashlib.sha256(data).hexdigest()


def _entry_for_repo(repo_name: str) -> dict[str, object] | None:
    manifest = _fetch_manifest(repo_name)
    if manifest is None:
        return None
    plugin_id = manifest.get("plugin_id")
    version = manifest.get("version") or "0.1.0"
    tier = manifest.get("tier") or "live"
    layer = manifest.get("permission_layer") or 1
    pii = bool(manifest.get("processes_pii", False))
    ack = manifest.get("pipa_trustee_acknowledgment") or {}
    trustee = ack.get("trustee_org_name") if isinstance(ack, dict) else None
    if not isinstance(plugin_id, str):
        return None

    sha = _bundle_sha(repo_name)
    if sha is None:
        return None

    name_no_prefix = repo_name[len(PLUGIN_PREFIX) :]
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    bundle_url = f"https://github.com/{ORG}/{repo_name}/archive/refs/heads/main.tar.gz"
    provenance_url = (
        f"https://github.com/{ORG}/{repo_name}/releases/download/"
        f"v{version}/{plugin_id}.intoto.jsonl"
    )
    return {
        "name": name_no_prefix,
        "plugin_id": plugin_id,
        "latest_version": version,
        "versions": [
            {
                "version": version,
                "bundle_url": bundle_url,
                "provenance_url": provenance_url,
                "bundle_sha256": sha,
                "published_iso": timestamp,
            }
        ],
        "tier": tier,
        "permission_layer": layer,
        "processes_pii": pii,
        "trustee_org_name": trustee,
        "last_published_iso": timestamp,
    }


def regenerate() -> dict[str, object]:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    repos = _list_plugin_repos()
    entries: list[dict[str, object]] = []
    for repo in repos:
        entry = _entry_for_repo(repo)
        if entry is not None:
            entries.append(entry)
    return {
        "schema_version": "1.0.0",
        "generated_iso": timestamp,
        "entries": entries,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="regenerate_catalog")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write to PATH (default: stdout).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "CI drift gate: read PATH (or kosmos-plugin-store/index/index.json) "
            "and exit non-zero if it differs from a freshly-regenerated index."
        ),
    )
    args = parser.parse_args(argv)

    fresh = regenerate()
    rendered = json.dumps(fresh, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if args.out is None:
            print("--check requires --out PATH pointing at the committed index.json", file=sys.stderr)
            return 2
        existing = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        # Drop generated_iso + per-version published_iso from BOTH sides — they
        # change on every regenerate. The drift gate compares the structural
        # shape only (entries / tier / sha / urls).
        def _strip_timestamps(payload: dict) -> dict:
            payload = json.loads(json.dumps(payload))
            payload.pop("generated_iso", None)
            for entry in payload.get("entries", []):
                entry.pop("last_published_iso", None)
                for v in entry.get("versions", []):
                    v.pop("published_iso", None)
            return payload

        existing_obj = json.loads(existing) if existing else {}
        if _strip_timestamps(existing_obj) != _strip_timestamps(fresh):
            print(
                "catalog drift detected — regenerate via "
                "`uv run python scripts/regenerate_catalog.py --out <path>`",
                file=sys.stderr,
            )
            return 1
        return 0

    if args.out is None:
        sys.stdout.write(rendered)
    else:
        args.out.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.out} ({len(fresh['entries'])} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
