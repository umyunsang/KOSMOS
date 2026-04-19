# SPDX-License-Identifier: Apache-2.0
"""CLI skeleton for the KOSMOS permissions subsystem (Spec 033 FR-D05).

Registered as ``kosmos-permissions`` entry point in ``pyproject.toml``.

Available subcommands:
  verify      — Verify consent ledger hash chain + HMAC seals.
  rotate-key  — Rotate the HMAC key (yearly; archives old key).
  allow       — Add an ``allow`` rule for an adapter.
  deny        — Add a ``deny`` rule for an adapter.
  ask         — Set a rule to ``ask`` (explicit "no decision").
  revoke      — Remove a rule for an adapter.
  list        — List current permission rules.

All handlers currently raise ``NotImplementedError``; they will be filled by
the WS2 (rule store), WS3 (ledger + CLI), and WS4 (prompt) workstream
Teammates in Phases 3-7.

Reference: specs/033-permission-v2-spectrum/contracts/ledger-verify.cli.md
"""

from __future__ import annotations

import argparse
import logging
import sys

__all__ = ["main"]

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subcommand handlers (stubs — filled by Phases 3-7)
# ---------------------------------------------------------------------------


def _cmd_verify(args: argparse.Namespace) -> int:
    """Verify the consent ledger hash chain and HMAC seals.

    Exit codes (contracts/ledger-verify.cli.md):
      0  — all checks passed
      1  — chain integrity failure
      2  — HMAC seal failure
      3  — key missing / unreadable
      4  — file corrupt / unreadable
      5  — schema violation
      6  — key file mode wrong
    """
    raise NotImplementedError(
        "kosmos-permissions verify: not yet implemented. "
        "Will be filled by WS3 (Phases 3-7)."
    )


def _cmd_rotate_key(args: argparse.Namespace) -> int:
    """Rotate the HMAC key.

    Archives the old key as ``keys/ledger.key.kNNNN`` and writes a new key
    with incremented key_id.  All new ledger records will use the new key.
    Old records remain verifiable via the archived key.
    """
    raise NotImplementedError(
        "kosmos-permissions rotate-key: not yet implemented. "
        "Will be filled by WS3 (Phases 3-7)."
    )


def _cmd_allow(args: argparse.Namespace) -> int:
    """Add an ``allow`` rule for an adapter.

    Writes the rule to ``~/.kosmos/permissions.json`` at ``user`` scope
    (or ``session`` scope if ``--session`` is passed).
    """
    raise NotImplementedError(
        "kosmos-permissions allow: not yet implemented. "
        "Will be filled by WS2 (Phases 3-7)."
    )


def _cmd_deny(args: argparse.Namespace) -> int:
    """Add a ``deny`` rule for an adapter.

    Deny rules are scope-sticky: they persist across sessions (``user`` scope)
    unless ``--session`` is passed.
    """
    raise NotImplementedError(
        "kosmos-permissions deny: not yet implemented. "
        "Will be filled by WS2 (Phases 3-7)."
    )


def _cmd_ask(args: argparse.Namespace) -> int:
    """Set a rule to ``ask`` (explicit acknowledgement, no persistent decision).

    Semantically equivalent to removing the rule (Invariant R3), but records
    the acknowledgement in the rule store.
    """
    raise NotImplementedError(
        "kosmos-permissions ask: not yet implemented. "
        "Will be filled by WS2 (Phases 3-7)."
    )


def _cmd_revoke(args: argparse.Namespace) -> int:
    """Remove a rule for an adapter.

    Removing a rule returns the adapter to the ``ask`` state (prompts on next
    invocation).  Cannot silently demote a ``deny`` rule (Invariant S2 from
    data-model.md § 3.2).
    """
    raise NotImplementedError(
        "kosmos-permissions revoke: not yet implemented. "
        "Will be filled by WS2 (Phases 3-7)."
    )


def _cmd_list(args: argparse.Namespace) -> int:
    """List current permission rules from ``~/.kosmos/permissions.json``."""
    raise NotImplementedError(
        "kosmos-permissions list: not yet implemented. "
        "Will be filled by WS2 (Phases 3-7)."
    )


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
        help="Verify hash chain only, skip HMAC seal verification.",
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
