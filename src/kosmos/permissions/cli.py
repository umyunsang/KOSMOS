# SPDX-License-Identifier: Apache-2.0
"""CLI for the KOSMOS permissions subsystem (Spec 033 FR-D05, FR-C05).

Registered as ``kosmos-permissions`` entry point in ``pyproject.toml``.

Available subcommands:
  verify      — Verify consent ledger hash chain + HMAC seals.  [WS3]
  rotate-key  — Rotate the HMAC key (yearly; archives old key).  [WS3]
  allow       — Add an ``allow`` rule for an adapter.  [WS2]
  deny        — Add a ``deny`` rule for an adapter.  [WS2]
  ask         — Set a rule to ``ask`` (explicit "no decision").  [WS2]
  revoke      — Remove a rule for an adapter.  [WS2]
  list        — List current permission rules.  [WS2]

Exit codes:
  0  — success
  1  — unexpected runtime error
  2  — invalid tool_id (pattern mismatch or too long)
  3  — schema error loading/saving the rule store
  64 — unimplemented command (WS3 stubs)

Reference: specs/033-permission-v2-spectrum/contracts/ledger-verify.cli.md
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import UTC
from pathlib import Path
from typing import Any

from kosmos.permissions.rules import (
    RuleStore,
    RuleStorePermissionsError,
    RuleStoreSchemaError,
    make_rule,
)
from kosmos.settings import settings

__all__ = ["main"]

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool-id validation (matches permissions-store.schema.json pattern)
# ---------------------------------------------------------------------------

_TOOL_ID_RE = re.compile(r"^[a-z0-9_.]+$")
_TOOL_ID_MAX_LEN = 128


def _validate_tool_id(tool_id: str) -> str | None:
    """Return None if valid, or an error message string if invalid."""
    if not tool_id:
        return "tool_id must not be empty"
    if len(tool_id) > _TOOL_ID_MAX_LEN:
        return f"tool_id exceeds {_TOOL_ID_MAX_LEN} characters"
    if not _TOOL_ID_RE.match(tool_id):
        return (
            f"tool_id {tool_id!r} does not match pattern ^[a-z0-9_.]+$"
            " (only lowercase letters, digits, underscores, dots)"
        )
    return None


def _load_store(store_path: Path) -> RuleStore | None:
    """Load the rule store, logging any errors.  Returns None on failure."""
    store = RuleStore(store_path)
    try:
        store.load()
    except (RuleStorePermissionsError, RuleStoreSchemaError) as exc:
        _logger.error("Failed to load rule store: %s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return None
    return store


# ---------------------------------------------------------------------------
# Subcommand handlers (stubs — filled by Phases 3-7)
# ---------------------------------------------------------------------------


def _cmd_verify(args: argparse.Namespace) -> int:  # noqa: C901
    """Verify the consent ledger hash chain and HMAC seals.

    Exit codes (contracts/ledger-verify.cli.md §2):
      0  — all checks passed
      1  — hash chain broken (CHAIN_RECORD_HASH_MISMATCH or CHAIN_PREV_HASH_MISMATCH)
      2  — HMAC seal mismatch
      3  — HMAC key unknown (key_id not in registry)
      4  — schema violation
      5  — file not found or empty
      6  — HMAC key file mode mismatch (expected 0400)
      64 — usage error (--hash-only without --acknowledge-key-loss)
    """
    import os as _os

    from kosmos.permissions.hmac_key import HMACKeyFileModeError
    from kosmos.permissions.ledger_verify import verify_ledger

    # ---- Parse verify-specific flags ----------------------------------------
    hash_only: bool = getattr(args, "hash_only", False)
    acknowledge_key_loss: bool = getattr(args, "acknowledge_key_loss", False)
    emit_json: bool = getattr(args, "json_output", False)

    # ---- Usage guard: --hash-only requires --acknowledge-key-loss -----------
    if hash_only and not acknowledge_key_loss:
        sys.stderr.write(
            "Error: --hash-only requires --acknowledge-key-loss.\n"
            "Usage: kosmos-permissions verify --hash-only --acknowledge-key-loss\n"
            "\nThis flag documents that HMAC verification is skipped due to key loss.\n"
        )
        return 64

    # ---- Resolve paths ------------------------------------------------------
    ledger_path: Path
    if getattr(args, "ledger", None):
        ledger_path = Path(args.ledger).expanduser().resolve()
    else:
        ledger_path = settings.permission_ledger_path

    key_path: Path
    if getattr(args, "key", None):
        key_path = Path(args.key).expanduser().resolve()
    else:
        key_path = settings.permission_key_path

    key_registry_path: Path = key_path.parent / "registry.json"

    # ---- Pre-check: HMAC key file mode (exit 6) ----------------------------
    if not hash_only and key_path.exists():
        stat = _os.stat(key_path)
        actual_mode = stat.st_mode & 0o777
        if actual_mode != 0o400:
            sys.stderr.write(
                f"Error: HMAC key file {key_path!r} has mode {oct(actual_mode)} "
                "but 0o400 is required.\n"
                f"Fix with: chmod 0400 {key_path}\n"
            )
            return 6

    # ---- Run verifier -------------------------------------------------------
    try:
        report = verify_ledger(
            ledger_path=ledger_path,
            key_registry_path=key_registry_path,
            hash_only=hash_only,
            acknowledge_key_loss=acknowledge_key_loss,
        )
    except HMACKeyFileModeError:
        sys.stderr.write(
            f"Error: HMAC key file has wrong permissions. Fix with: chmod 0400 {key_path}\n"
        )
        return 6
    except OSError as exc:
        sys.stderr.write(f"Error: Failed to read ledger: {exc}\n")
        return 5

    # ---- Emit output --------------------------------------------------------
    exit_code = report.exit_code

    if emit_json:
        # Derive chain_ok / hmac_ok from broken_reason.
        chain_ok: bool
        hmac_ok: bool
        if report.passed:
            chain_ok = True
            hmac_ok = True
        elif report.broken_reason in ("CHAIN_RECORD_HASH_MISMATCH", "CHAIN_PREV_HASH_MISMATCH"):
            chain_ok = False
            hmac_ok = True
        elif report.broken_reason == "HMAC_SEAL_MISMATCH":
            chain_ok = True
            hmac_ok = False
        else:
            chain_ok = False
            hmac_ok = False

        output = {
            "total_records": report.total_records,
            "chain_ok": chain_ok,
            "hmac_ok": hmac_ok,
            "first_broken_index": report.first_broken_index,
            "broken_reason": report.broken_reason,
            "exit_code": exit_code,
            "path": str(ledger_path),
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    else:
        # Human-readable mode.
        if report.passed:
            sys.stdout.write(
                "Ledger verification PASSED\n"
                f"  Path: {ledger_path}\n"
                f"  Records: {report.total_records}\n"
                "  Chain: OK\n"
                "  HMAC: OK\n"
            )
        else:
            reason = report.broken_reason or "UNKNOWN"
            sys.stdout.write(
                f"Ledger verification FAILED -- {reason}\n"
                f"  Path: {ledger_path}\n"
                f"  Records: {report.total_records}\n"
            )
            if report.first_broken_index is not None:
                sys.stdout.write(f"  First broken index: {report.first_broken_index}\n")
            if exit_code == 5:
                sys.stdout.write("  Reason: Ledger file not found or empty.\n")
            elif exit_code == 3:
                sys.stdout.write(
                    "  Reason: HMAC key_id not found in registry.\n"
                    "  Use --hash-only --acknowledge-key-loss to skip HMAC.\n"
                )
            elif exit_code == 4:
                sys.stdout.write("  Reason: Record fails ConsentLedgerRecord schema validation.\n")

    return exit_code


def _cmd_rotate_key(args: argparse.Namespace) -> int:  # noqa: C901
    """Rotate the HMAC key.

    Archives ``keys/ledger.key`` → ``keys/ledger.key.kNNNN`` (next sequence).
    Generates a new key at ``keys/ledger.key`` with mode 0o400.
    Updates ``keys/registry.json`` with the retired key entry + new active entry.
    All existing ledger records remain verifiable via the archived key (Invariant L4).
    """
    import os as _os
    import secrets as _secrets
    from datetime import datetime

    key_path: Path
    if getattr(args, "key", None):
        key_path = Path(args.key).expanduser().resolve()
    else:
        key_path = settings.permission_key_path

    keys_dir = key_path.parent
    registry_path = keys_dir / "registry.json"

    # ---- Determine next key_id sequence ------------------------------------
    next_seq = 1
    existing_entries: list[dict[str, Any]] = []

    if registry_path.exists():
        try:
            existing_entries = json.loads(registry_path.read_text("utf-8"))
            if isinstance(existing_entries, list):
                for entry in existing_entries:
                    kid = entry.get("key_id", "k0000")
                    try:
                        seq = int(str(kid).lstrip("k"))
                        if seq >= next_seq:
                            next_seq = seq + 1
                    except (ValueError, AttributeError):
                        pass
        except (json.JSONDecodeError, OSError):
            existing_entries = []

    # The key being retired is the currently active key.
    # If the registry is absent but a key file exists, it was the implicit
    # k0001 (created by the first `ledger.append` call); treat it as sequence
    # 1 so the new key gets sequence 2, avoiding a key_id collision that
    # would otherwise overwrite the archived key in verify-time dicts.
    if next_seq == 1 and key_path.exists():
        next_seq = 2
    current_key_id = f"k{(next_seq - 1):04d}" if next_seq > 1 else "k0001"
    new_key_id = f"k{next_seq:04d}"

    retired_at = datetime.now(tz=UTC).isoformat()
    archive_filename = f"ledger.key.{current_key_id}"
    archive_path = keys_dir / archive_filename

    if key_path.exists():
        # Read current key bytes.
        current_key_bytes = key_path.read_bytes()
        # Write archive copy with mode 0o400.
        archive_fd = _os.open(str(archive_path), _os.O_WRONLY | _os.O_CREAT | _os.O_EXCL, 0o400)
        try:
            _os.write(archive_fd, current_key_bytes)
        finally:
            _os.close(archive_fd)
        # Remove current key so we can create the new one.
        _os.unlink(str(key_path))
        _logger.info("Archived key %s to %s", current_key_id, archive_path)

        # Update retired entry for current_key_id in registry.
        updated = False
        for entry in existing_entries:
            if entry.get("key_id") == current_key_id:
                entry["retired_at"] = retired_at
                entry["file_path"] = archive_filename
                updated = True
                break
        if not updated:
            existing_entries.append(
                {
                    "key_id": current_key_id,
                    "retired_at": retired_at,
                    "file_path": archive_filename,
                }
            )
    else:
        _logger.info("No existing key at %s; generating first key", key_path)

    # ---- Generate new key --------------------------------------------------
    keys_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    new_key_bytes = _secrets.token_bytes(32)
    new_key_fd = _os.open(str(key_path), _os.O_WRONLY | _os.O_CREAT | _os.O_EXCL, 0o400)
    try:
        _os.write(new_key_fd, new_key_bytes)
    finally:
        _os.close(new_key_fd)

    _logger.info("Generated new HMAC key %s at %s (mode 0400)", new_key_id, key_path)

    # ---- Add new active key to registry ------------------------------------
    existing_entries.append(
        {
            "key_id": new_key_id,
            "retired_at": None,
            "file_path": "ledger.key",
        }
    )

    # Atomic registry write (tmp + rename).
    tmp_registry = registry_path.with_suffix(".json.tmp")
    tmp_registry.write_text(
        json.dumps(existing_entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _os.rename(str(tmp_registry), str(registry_path))

    sys.stdout.write(
        "Key rotation complete.\n"
        f"  Retired: {current_key_id} -> {archive_filename}\n"
        f"  New active key: {new_key_id} ({key_path})\n"
        f"  Registry: {registry_path}\n"
    )
    return 0


def _cmd_allow(args: argparse.Namespace) -> int:
    """Add an ``allow`` rule for an adapter (WS2 — T038).

    Writes the rule to ``~/.kosmos/permissions.json`` at ``user`` scope
    (or keeps in-memory at ``session`` scope if ``--session`` is passed).

    Exit codes:
      0  — success
      2  — invalid tool_id
      3  — schema error
    """
    tool_id: str = args.tool_id
    err = _validate_tool_id(tool_id)
    if err:
        sys.stderr.write(f"Error: {err}\n")
        return 2

    store_path: Path = settings.permission_rule_store_path
    scope = "session" if getattr(args, "session", False) else "user"

    if scope == "session":
        # Session-scope rules are in-memory only; just confirm to the user.
        sys.stdout.write(f"[session] allow {tool_id!r} (in-memory only, not persisted)\n")
        return 0

    store = _load_store(store_path)
    if store is None:
        # Schema or permissions error already logged; start fresh for this write.
        _logger.info("Starting with empty rule store for allow write")
        store = RuleStore(store_path)

    rule = make_rule(tool_id=tool_id, decision="allow", scope="user", mode="default")
    try:
        store.save_rule(rule)
    except RuleStoreSchemaError as exc:
        _logger.error("Schema error saving allow rule: %s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 3

    sys.stdout.write(f"[user] allow {tool_id!r} — saved to {store_path}\n")
    return 0


def _cmd_deny(args: argparse.Namespace) -> int:
    """Add a ``deny`` rule for an adapter (WS2 — T038).

    Deny rules are scope-sticky: they persist across sessions (``user`` scope)
    unless ``--session`` is passed.

    Exit codes:
      0  — success
      2  — invalid tool_id
      3  — schema error
    """
    tool_id: str = args.tool_id
    err = _validate_tool_id(tool_id)
    if err:
        sys.stderr.write(f"Error: {err}\n")
        return 2

    store_path: Path = settings.permission_rule_store_path
    scope = "session" if getattr(args, "session", False) else "user"

    if scope == "session":
        sys.stdout.write(f"[session] deny {tool_id!r} (in-memory only, not persisted)\n")
        return 0

    store = _load_store(store_path)
    if store is None:
        store = RuleStore(store_path)

    rule = make_rule(tool_id=tool_id, decision="deny", scope="user", mode="default")
    try:
        store.save_rule(rule)
    except RuleStoreSchemaError as exc:
        _logger.error("Schema error saving deny rule: %s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 3

    sys.stdout.write(f"[user] deny {tool_id!r} — saved to {store_path}\n")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    """Set a rule to ``ask`` (explicit acknowledgement, no persistent decision) — T038.

    Semantically equivalent to removing the rule (Invariant R3), but records
    the acknowledgement in the rule store so audit trails reflect the decision.

    Exit codes:
      0  — success
      2  — invalid tool_id
      3  — schema error
    """
    tool_id: str = args.tool_id
    err = _validate_tool_id(tool_id)
    if err:
        sys.stderr.write(f"Error: {err}\n")
        return 2

    store_path: Path = settings.permission_rule_store_path

    store = _load_store(store_path)
    if store is None:
        store = RuleStore(store_path)

    rule = make_rule(tool_id=tool_id, decision="ask", scope="user", mode="default")
    try:
        store.save_rule(rule)
    except RuleStoreSchemaError as exc:
        _logger.error("Schema error saving ask rule: %s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 3

    sys.stdout.write(f"[user] ask {tool_id!r} — saved to {store_path}\n")
    return 0


def _cmd_revoke(args: argparse.Namespace) -> int:
    """Remove a rule for an adapter (WS2 — T038).

    Removing a rule returns the adapter to the ``ask`` state (prompts on next
    invocation).  For ``user`` scope the change is persisted atomically.

    Exit codes:
      0  — success (including "rule not found" — idempotent)
      2  — invalid tool_id
      3  — schema error
    """
    tool_id: str = args.tool_id
    err = _validate_tool_id(tool_id)
    if err:
        sys.stderr.write(f"Error: {err}\n")
        return 2

    scope: str = getattr(args, "scope", "user")
    store_path: Path = settings.permission_rule_store_path

    store = _load_store(store_path)
    if store is None:
        store = RuleStore(store_path)

    try:
        removed = store.revoke(tool_id=tool_id, scope=scope)  # type: ignore[arg-type]
    except RuleStoreSchemaError as exc:
        _logger.error("Schema error revoking rule: %s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 3

    if removed:
        sys.stdout.write(f"[{scope}] revoked rule for {tool_id!r}\n")
    else:
        sys.stdout.write(f"[{scope}] no rule found for {tool_id!r} (nothing to revoke)\n")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    """List current permission rules from ``~/.kosmos/permissions.json`` — T038.

    Exit codes:
      0  — success
      3  — schema error loading the rule store
    """
    store_path: Path = settings.permission_rule_store_path
    scope: str = getattr(args, "scope", "all")
    output_format: str = getattr(args, "output_format", "table")

    store = _load_store(store_path)
    if store is None:
        sys.stderr.write("Error: could not load rule store — see above for details.\n")
        return 3

    rules = store.list_rules(scope=scope)  # type: ignore[arg-type]

    if output_format == "json":
        rule_dicts = [
            {
                "tool_id": r.tool_id,
                "decision": r.decision,
                "scope": r.scope,
                "created_at": r.created_at.isoformat(),
                "created_by_mode": r.created_by_mode,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rules
        ]
        sys.stdout.write(json.dumps(rule_dicts, indent=2, ensure_ascii=False) + "\n")
    else:
        # Table format
        if not rules:
            sys.stdout.write("No rules found.\n")
        else:
            header = (
                f"{'TOOL_ID':<40} {'DECISION':<8} {'SCOPE':<10} {'CREATED_AT':<26} {'MODE':<20}"
            )
            sys.stdout.write(header + "\n")
            sys.stdout.write("-" * len(header) + "\n")
            for r in rules:
                expires = f" [expires {r.expires_at.isoformat()}]" if r.expires_at else ""
                row = (
                    f"{r.tool_id:<40} {r.decision:<8} {r.scope:<10} "
                    f"{r.created_at.isoformat():<26} {r.created_by_mode:<20}{expires}"
                )
                sys.stdout.write(row + "\n")

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="kosmos-permissions",
        description=(
            "KOSMOS permission management CLI.\n\n"
            "Manages the consent ledger, HMAC keys, and per-adapter permission "
            "rules for the citizen-facing public API harness."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="kosmos-permissions 1.0.0 (Spec 033)",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="subcommand",
        metavar="<command>",
    )
    subparsers.required = True

    # --- verify ---
    p_verify = subparsers.add_parser(
        "verify",
        help="Verify consent ledger integrity (hash chain + HMAC seals).",
    )
    p_verify.add_argument(
        "--ledger",
        metavar="PATH",
        default=None,
        help="Path to the consent ledger JSONL file (default: KOSMOS_PERMISSION_LEDGER_PATH).",
    )
    p_verify.add_argument(
        "--key",
        metavar="PATH",
        default=None,
        help="Path to the HMAC key file (default: KOSMOS_PERMISSION_KEY_PATH).",
    )
    p_verify.add_argument(
        "--hash-only",
        action="store_true",
        default=False,
        dest="hash_only",
        help=(
            "Skip HMAC verification. Use only when HMAC key is lost. "
            "Requires --acknowledge-key-loss."
        ),
    )
    p_verify.add_argument(
        "--acknowledge-key-loss",
        action="store_true",
        default=False,
        dest="acknowledge_key_loss",
        help=(
            "Required alongside --hash-only. Documents that HMAC step is skipped due to key loss."
        ),
    )
    p_verify.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Emit LedgerVerifyReport as JSON (for CI / audit pipelines).",
    )
    p_verify.set_defaults(func=_cmd_verify)

    # --- rotate-key ---
    p_rotate = subparsers.add_parser(
        "rotate-key",
        help="Rotate the HMAC key (archives old key, generates new key).",
    )
    p_rotate.add_argument(
        "--key",
        metavar="PATH",
        default=None,
        help="Path to the HMAC key file (default: KOSMOS_PERMISSION_KEY_PATH).",
    )
    p_rotate.set_defaults(func=_cmd_rotate_key)

    # --- allow ---
    p_allow = subparsers.add_parser(
        "allow",
        help="Add an allow rule for an adapter.",
    )
    p_allow.add_argument("tool_id", help="Adapter identifier (e.g. hira_hospital_search).")
    p_allow.add_argument(
        "--session",
        action="store_true",
        default=False,
        help="Session scope only (not persisted to disk).",
    )
    p_allow.set_defaults(func=_cmd_allow)

    # --- deny ---
    p_deny = subparsers.add_parser(
        "deny",
        help="Add a deny rule for an adapter.",
    )
    p_deny.add_argument("tool_id", help="Adapter identifier.")
    p_deny.add_argument(
        "--session",
        action="store_true",
        default=False,
        help="Session scope only (not persisted to disk).",
    )
    p_deny.set_defaults(func=_cmd_deny)

    # --- ask ---
    p_ask = subparsers.add_parser(
        "ask",
        help="Set a rule to ask (explicit acknowledgement, no persistent decision).",
    )
    p_ask.add_argument("tool_id", help="Adapter identifier.")
    p_ask.set_defaults(func=_cmd_ask)

    # --- revoke ---
    p_revoke = subparsers.add_parser(
        "revoke",
        help="Remove a rule for an adapter.",
    )
    p_revoke.add_argument("tool_id", help="Adapter identifier.")
    p_revoke.add_argument(
        "--scope",
        choices=["session", "project", "user"],
        default="user",
        help="Scope of rule to revoke (default: user).",
    )
    p_revoke.set_defaults(func=_cmd_revoke)

    # --- list ---
    p_list = subparsers.add_parser(
        "list",
        help="List current permission rules.",
    )
    p_list.add_argument(
        "--scope",
        choices=["session", "project", "user", "all"],
        default="all",
        help="Filter by scope (default: all).",
    )
    p_list.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        dest="output_format",
        help="Output format (default: table).",
    )
    p_list.set_defaults(func=_cmd_list)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the ``kosmos-permissions`` CLI.

    Registered in ``pyproject.toml`` as::

        [project.scripts]
        kosmos-permissions = "kosmos.permissions.cli:main"
    """
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    parser = _build_parser()
    args = parser.parse_args()

    try:
        exit_code = args.func(args)
        sys.exit(exit_code if isinstance(exit_code, int) else 0)
    except NotImplementedError as exc:
        # During Phase 1+2 scaffolding, all handlers raise NotImplementedError.
        # Report clearly so callers know this is intentional stub behaviour.
        _logger.error("Not yet implemented: %s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(64)  # EX_USAGE — functionally similar to "command not supported yet"
    except Exception as exc:  # noqa: BLE001
        _logger.exception("Unexpected error in kosmos-permissions %s", args.subcommand)
        sys.stderr.write(f"Unexpected error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
