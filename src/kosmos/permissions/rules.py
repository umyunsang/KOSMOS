# SPDX-License-Identifier: Apache-2.0
"""Tri-state persistent rule store — Spec 033 FR-C01..FR-C05.

Provides ``RuleStore``: an in-memory registry of ``PermissionRule`` objects
backed by ``~/.kosmos/permissions.json`` (path configurable via
``KOSMOS_PERMISSION_RULE_STORE_PATH``).

Invariants
----------
R1 (deny-wins)
    If *any* rule in the scope resolution chain returns ``deny``, the final
    decision is ``deny``, regardless of other rules.
R2 (narrower-wins)
    Scope precedence: ``session`` > ``project`` > ``user``.  The narrowest
    (most specific) non-ask rule wins.
R3 (ask ≡ no-rule)
    An explicit ``ask`` rule is semantically identical to "no persistent
    decision".  ``resolve()`` returns ``None`` when the effective decision
    is ``ask``.
C3 (file mode 0o600)
    ``load()`` refuses to read a file whose mode is not 0o600.  Raises
    ``RuleStorePermissionsError``.
FR-C02 (fail-closed on schema violation)
    ``load()`` raises ``RuleStoreSchemaError`` on any JSON parsing error or
    schema violation.  Callers are expected to catch this, reset the mode to
    ``default``, and continue without rules.
FR-C03 (atomic write)
    ``save_rule()`` writes to a ``.tmp`` sibling file first, fsyncs, sets
    mode 0o600, then ``os.rename()``s atomically (POSIX).
M3 / PR1 (mode never persists)
    This module only stores *rules*, never the active ``PermissionMode``.
    Mode reset on restart is the caller's responsibility (see
    ``session_boot.reset_session_state()``).

Schema
------
The on-disk format is validated against
``specs/033-permission-v2-spectrum/contracts/permissions-store.schema.json``
at load time.  The validation is hand-rolled (stdlib-only — ``jsonschema``
is only in the dev dependency group, AGENTS.md hard rule forbids new
runtime deps).
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kosmos.permissions.models import PermissionRule
from kosmos.permissions.modes import PermissionMode

__all__ = [
    "RuleStore",
    "RuleStorePermissionsError",
    "RuleStoreSchemaError",
    "ScopeContext",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1.0.0"
_TOOL_ID_RE = re.compile(r"^[a-z0-9_.]+$")
_VALID_DECISIONS: frozenset[str] = frozenset({"allow", "ask", "deny"})
_VALID_SCOPES: frozenset[str] = frozenset({"session", "project", "user"})
_VALID_MODES: frozenset[str] = frozenset(
    {"default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"}
)

# Scope priority order (narrower = higher priority).
_SCOPE_PRIORITY: dict[str, int] = {"session": 0, "project": 1, "user": 2}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RuleStorePermissionsError(Exception):
    """Raised when ``permissions.json`` has wrong file-system permissions.

    Per Invariant C3: the file MUST be mode 0o600.  Any other mode raises
    this error so the caller can fail closed.
    """


class RuleStoreSchemaError(Exception):
    """Raised when ``permissions.json`` fails validation (FR-C02).

    Callers MUST catch this and fall back to ``default`` mode with no rules.
    """


# ---------------------------------------------------------------------------
# ScopeContext — injected by the pipeline to indicate current session/project
# ---------------------------------------------------------------------------


class ScopeContext(BaseModel):
    """Lightweight context injected by the permission pipeline for resolution.

    Contains the in-memory session and project rules that exist only for the
    lifetime of the current process.  ``user``-scope rules come from disk.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    session_rules: tuple[PermissionRule, ...] = Field(default=())
    """In-memory ``session``-scoped rules (cleared on process exit)."""

    project_rules: tuple[PermissionRule, ...] = Field(default=())
    """In-memory ``project``-scoped rules (cleared on process exit)."""


# ---------------------------------------------------------------------------
# Schema validation helpers (hand-rolled; no jsonschema runtime dep)
# ---------------------------------------------------------------------------


def _validate_rule_shape(idx: int, rule: dict[str, object]) -> None:
    """Validate required presence and absence of fields on a rule dict."""
    for req in ("tool_id", "decision", "scope", "created_at", "created_by_mode"):
        if req not in rule:
            raise RuleStoreSchemaError(f"Rule[{idx}] missing required field: {req!r}")
    # Extra fields — additionalProperties: false
    allowed = {"tool_id", "decision", "scope", "created_at", "created_by_mode", "expires_at"}
    extra = set(rule.keys()) - allowed
    if extra:
        raise RuleStoreSchemaError(
            f"Rule[{idx}] has additional properties not permitted by schema: {extra!r}"
        )


def _validate_rule_fields(idx: int, rule: dict[str, object]) -> None:
    """Validate the individual field values of an already-shape-checked rule dict."""
    tool_id = rule["tool_id"]
    if not isinstance(tool_id, str) or not tool_id:
        raise RuleStoreSchemaError(f"Rule[{idx}].tool_id must be a non-empty string")
    if len(tool_id) > 128:
        raise RuleStoreSchemaError(f"Rule[{idx}].tool_id exceeds 128 characters")
    if not _TOOL_ID_RE.match(tool_id):
        raise RuleStoreSchemaError(
            f"Rule[{idx}].tool_id {tool_id!r} does not match pattern ^[a-z0-9_.]+$"
        )

    decision = rule["decision"]
    if decision not in _VALID_DECISIONS:
        raise RuleStoreSchemaError(
            f"Rule[{idx}].decision must be one of {sorted(_VALID_DECISIONS)!r}, got {decision!r}"
        )

    scope = rule["scope"]
    if scope not in _VALID_SCOPES:
        raise RuleStoreSchemaError(
            f"Rule[{idx}].scope must be one of {sorted(_VALID_SCOPES)!r}, got {scope!r}"
        )

    mode = rule["created_by_mode"]
    if mode not in _VALID_MODES:
        raise RuleStoreSchemaError(
            f"Rule[{idx}].created_by_mode must be one of {sorted(_VALID_MODES)!r}, got {mode!r}"
        )

    _parse_datetime_field(rule, f"Rule[{idx}].created_at", "created_at")
    if rule.get("expires_at") is not None:
        _parse_datetime_field(rule, f"Rule[{idx}].expires_at", "expires_at")


def _validate_rule_object(idx: int, rule: object) -> None:
    """Validate a single rule dict against the permissions-store JSON schema.

    Raises ``RuleStoreSchemaError`` on any violation.
    """
    if not isinstance(rule, dict):
        raise RuleStoreSchemaError(f"Rule[{idx}] is not an object")
    _validate_rule_shape(idx, rule)
    _validate_rule_fields(idx, rule)


def _parse_datetime_field(obj: dict[str, object], label: str, key: str) -> None:
    """Parse an ISO 8601 datetime field, raising RuleStoreSchemaError on failure."""
    val = obj[key]
    if val is None and key == "expires_at":
        return
    if not isinstance(val, str):
        raise RuleStoreSchemaError(f"{label} must be a string, got {type(val).__name__!r}")
    try:
        datetime.fromisoformat(val)
    except ValueError as exc:
        raise RuleStoreSchemaError(f"{label} is not a valid ISO 8601 datetime: {val!r}") from exc


def _validate_store_document(doc: object) -> None:
    """Validate the top-level permissions-store document.

    Raises ``RuleStoreSchemaError`` on any violation.
    """
    if not isinstance(doc, dict):
        raise RuleStoreSchemaError("permissions.json root must be a JSON object")

    # additionalProperties: false — only allow declared keys
    allowed_top = {"schema_version", "generated_at", "rules"}
    extra = set(doc.keys()) - allowed_top
    if extra:
        raise RuleStoreSchemaError(
            f"permissions.json has additional properties not permitted by schema: {extra!r}"
        )

    # required: schema_version, rules
    if "schema_version" not in doc:
        raise RuleStoreSchemaError("permissions.json missing required field: 'schema_version'")
    if "rules" not in doc:
        raise RuleStoreSchemaError("permissions.json missing required field: 'rules'")

    sv = doc["schema_version"]
    if sv != _SCHEMA_VERSION:
        raise RuleStoreSchemaError(
            f"permissions.json schema_version {sv!r} != expected {_SCHEMA_VERSION!r}"
        )

    rules = doc["rules"]
    if not isinstance(rules, list):
        raise RuleStoreSchemaError("permissions.json 'rules' must be an array")

    for idx, rule in enumerate(rules):
        _validate_rule_object(idx, rule)


# ---------------------------------------------------------------------------
# RuleStore
# ---------------------------------------------------------------------------


class RuleStore:
    """Persistent tri-state rule registry backed by ``~/.kosmos/permissions.json``.

    Thread-safety
    -------------
    ``RuleStore`` is designed for single-process, single-threaded use (the
    KOSMOS harness is a single-user local process).  Concurrent writes from
    multiple processes are serialised via ``os.rename()`` atomicity — the last
    writer wins — which is acceptable at this cardinality (O(10²) rules).

    No I/O occurs in ``resolve()`` — it operates on the in-memory registry
    loaded by ``load()``.  This guarantees the p50 ≤ 5 ms latency budget
    (SC-008) is met with margin.
    """

    def __init__(self, store_path: Path) -> None:
        """Initialise with the given store path (not loaded yet).

        Args:
            store_path: Absolute path to ``permissions.json``.
        """
        self._path = store_path
        # Keyed by (tool_id, scope) → PermissionRule.  Populated by load().
        self._user_rules: dict[tuple[str, str], PermissionRule] = {}

    # ------------------------------------------------------------------
    # Load from disk
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load and validate ``permissions.json`` from disk into memory.

        Validates:
        1. File existence (if absent, rules are cleared and returns silently).
        2. File mode == 0o600 (Invariant C3 — raises ``RuleStorePermissionsError``).
        3. JSON parse success (raises ``RuleStoreSchemaError`` on failure).
        4. Schema conformance (raises ``RuleStoreSchemaError`` on violation).

        After a successful call the in-memory registry reflects the file.
        On any error the registry is cleared before the exception is raised.

        Raises:
            RuleStorePermissionsError: File mode is not 0o600.
            RuleStoreSchemaError: File content is invalid JSON or fails
                schema validation.
        """
        self._user_rules = {}

        if not self._path.exists():
            logger.debug(
                "permissions.json not found at %s — starting with empty rule set", self._path
            )
            return

        # --- Invariant C3: file mode check ---
        st = os.stat(self._path)
        actual_mode = stat_mode_octal(st.st_mode)
        if actual_mode != 0o600:
            raise RuleStorePermissionsError(
                f"permissions.json at {self._path} has mode {oct(actual_mode)} — "
                f"expected 0o600 (Invariant C3).  Fix with: chmod 600 {self._path}"
            )

        # --- Parse JSON ---
        try:
            raw = self._path.read_text(encoding="utf-8")
            doc = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuleStoreSchemaError(f"permissions.json is not valid JSON: {exc}") from exc
        except OSError as exc:
            raise RuleStoreSchemaError(f"Cannot read permissions.json: {exc}") from exc

        # --- Validate schema (hand-rolled, no jsonschema dep) ---
        _validate_store_document(doc)

        # --- Load rules into memory (user-scope only; others are in-memory) ---
        loaded = 0
        for rule_dict in doc["rules"]:
            # Only user-scope rules are stored on disk (schema permits project/session
            # in the array for forward-compatibility, but we only load user-scope here).
            if rule_dict.get("scope") != "user":
                logger.warning(
                    "Ignoring non-user-scope rule in permissions.json: %r (scope=%r)",
                    rule_dict.get("tool_id"),
                    rule_dict.get("scope"),
                )
                continue

            rule = _rule_dict_to_model(rule_dict)
            key = (rule.tool_id, rule.scope)
            if key in self._user_rules:
                # Last writer wins — later rule in the array takes precedence.
                logger.debug(
                    "Duplicate rule for (%r, %r) — last entry wins", rule.tool_id, rule.scope
                )
            self._user_rules[key] = rule
            loaded += 1

        logger.debug("Loaded %d user-scope rules from %s", loaded, self._path)

    # ------------------------------------------------------------------
    # Resolve — no I/O, pure in-memory
    # ------------------------------------------------------------------

    def resolve(
        self,
        tool_id: str,
        scope_ctx: ScopeContext,
    ) -> Literal["allow", "deny"] | None:
        """Resolve the effective decision for *tool_id*.

        Applies Invariants R1, R2, R3 in order:

        1. Collect all active, non-expired rules for *tool_id* across all
           scopes (session → project → user).
        2. If *any* rule is ``deny``, return ``"deny"`` (R1 deny-wins).
        3. Find the narrowest-scope ``allow`` rule; return ``"allow"`` if
           found (R2 narrower-wins).
        4. ``ask`` and "no rule" are both treated as ``None`` (R3 ask≡no-rule).

        No I/O occurs here.  Call ``load()`` first to populate the registry.

        Args:
            tool_id: Canonical adapter identifier to resolve.
            scope_ctx: In-memory session/project rules for the current session.

        Returns:
            ``"allow"`` or ``"deny"`` if a definitive rule is found;
            ``None`` when the effective decision is ``ask`` or there is no rule.
        """
        now = datetime.now(tz=UTC)

        # Gather all rules for this tool_id across all scopes, ordered from
        # narrowest to widest: session → project → user.
        candidates: list[PermissionRule] = []

        for rule in scope_ctx.session_rules:
            if rule.tool_id == tool_id and _is_active(rule, now):
                candidates.append(rule)

        for rule in scope_ctx.project_rules:
            if rule.tool_id == tool_id and _is_active(rule, now):
                candidates.append(rule)

        user_rule = self._user_rules.get((tool_id, "user"))
        if user_rule is not None and _is_active(user_rule, now):
            candidates.append(user_rule)

        if not candidates:
            return None  # R3: no rule ≡ ask

        # R1: deny-wins — any deny across any scope → deny
        if any(r.decision == "deny" for r in candidates):
            return "deny"

        # R2: narrower-wins — find the narrowest allow
        # candidates are already in narrowest-first order (session → project → user)
        for rule in candidates:
            if rule.decision == "allow":
                return "allow"

        # All remaining rules are "ask" → R3: treat as no decision
        return None

    # ------------------------------------------------------------------
    # Save (atomic write, FR-C03)
    # ------------------------------------------------------------------

    def save_rule(self, rule: PermissionRule) -> None:
        """Persist a ``user``-scope rule to disk via atomic write.

        Only ``user``-scope rules are persisted.  Session/project rules must
        not be passed here.  The in-memory registry is updated atomically with
        the disk write so ``resolve()`` reflects the change immediately.

        Atomic write protocol (FR-C03):
        1. Write full JSON to ``permissions.json.tmp`` with mode 0o600.
        2. ``os.fsync()`` the temp file descriptor.
        3. ``os.rename(tmp, final)`` — POSIX atomic.

        Args:
            rule: The rule to persist.  Must have ``scope == "user"``.

        Raises:
            ValueError: If ``rule.scope != "user"``.
            RuleStoreSchemaError: If the resulting store document fails
                schema validation (defensive; normally unreachable).
        """
        if rule.scope != "user":
            raise ValueError(
                f"save_rule() only persists user-scope rules; got scope={rule.scope!r}"
            )

        # Update in-memory registry first (so resolve() sees it regardless of I/O).
        key = (rule.tool_id, rule.scope)
        self._user_rules[key] = rule

        self._write_to_disk()
        logger.debug("Saved rule for tool_id=%r decision=%r", rule.tool_id, rule.decision)

    def revoke(self, tool_id: str, scope: Literal["session", "project", "user"]) -> bool:
        """Remove a rule from the registry.

        For ``user`` scope the change is also persisted atomically.  For
        ``session`` / ``project`` scope only the in-memory registry is updated
        (the caller is responsible for managing those rules).

        Args:
            tool_id: Adapter identifier whose rule to remove.
            scope: Scope from which to remove the rule.

        Returns:
            ``True`` if a rule was found and removed; ``False`` otherwise.
        """
        key = (tool_id, scope)
        if key not in self._user_rules:
            logger.debug("revoke() — no %r-scope rule found for tool_id=%r", scope, tool_id)
            return False

        del self._user_rules[key]

        if scope == "user":
            self._write_to_disk()
            logger.debug("Revoked user-scope rule for tool_id=%r", tool_id)

        return True

    def list_rules(
        self, scope: Literal["session", "project", "user", "all"] = "all"
    ) -> list[PermissionRule]:
        """Return all rules matching the given scope filter.

        Args:
            scope: ``"all"`` returns every rule in the in-memory registry.
                Other values filter to the specified scope.

        Returns:
            List of ``PermissionRule`` objects sorted by ``tool_id``.
        """
        rules = list(self._user_rules.values())
        if scope != "all":
            rules = [r for r in rules if r.scope == scope]
        return sorted(rules, key=lambda r: (r.tool_id, r.scope))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_to_disk(self) -> None:
        """Atomically write the current user-scope registry to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".json.tmp")

        user_rules = sorted(self._user_rules.values(), key=lambda r: r.tool_id)
        doc: dict[str, object] = {
            "schema_version": _SCHEMA_VERSION,
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "rules": [_rule_model_to_dict(r) for r in user_rules],
        }

        # Validate before writing (defensive — should never fail from our own data).
        _validate_store_document(doc)

        json_bytes = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")

        # Write to tmp with mode 0o600.
        fd = os.open(
            str(tmp_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        try:
            os.write(fd, json_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)

        # Ensure mode is 0o600 before rename (os.open sets it, but be explicit).
        os.chmod(str(tmp_path), 0o600)

        # POSIX atomic rename.
        os.rename(str(tmp_path), str(self._path))
        logger.debug("Atomically wrote permissions.json (%d bytes)", len(json_bytes))


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def stat_mode_octal(st_mode: int) -> int:
    """Extract the octal permission bits from an ``os.stat()`` mode integer."""
    return st_mode & 0o777


def _is_active(rule: PermissionRule, now: datetime) -> bool:
    """Return True if *rule* is not yet expired."""
    if rule.expires_at is None:
        return True
    return rule.expires_at > now


def _rule_model_to_dict(rule: PermissionRule) -> dict[str, object]:
    """Serialise a ``PermissionRule`` to a JSON-compatible dict."""
    return {
        "tool_id": rule.tool_id,
        "decision": rule.decision,
        "scope": rule.scope,
        "created_at": rule.created_at.isoformat(),
        "created_by_mode": rule.created_by_mode,
        "expires_at": rule.expires_at.isoformat() if rule.expires_at else None,
    }


def _rule_dict_to_model(d: dict[str, object]) -> PermissionRule:
    """Deserialise a validated rule dict to a ``PermissionRule`` model."""
    created_at_raw = d["created_at"]
    assert isinstance(created_at_raw, str)
    created_at = datetime.fromisoformat(created_at_raw)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    expires_at: datetime | None = None
    raw_expires = d.get("expires_at")
    if raw_expires is not None:
        assert isinstance(raw_expires, str)
        expires_at = datetime.fromisoformat(raw_expires)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

    decision = d["decision"]
    scope = d["scope"]
    created_by_mode = d["created_by_mode"]
    tool_id = d["tool_id"]

    assert isinstance(tool_id, str)
    assert isinstance(decision, str)
    assert isinstance(scope, str)
    assert isinstance(created_by_mode, str)

    return PermissionRule(
        tool_id=tool_id,
        decision=decision,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        created_at=created_at,
        created_by_mode=created_by_mode,  # type: ignore[arg-type]
        expires_at=expires_at,
    )


def make_rule(
    tool_id: str,
    decision: Literal["allow", "ask", "deny"],
    scope: Literal["session", "project", "user"],
    mode: PermissionMode = "default",
    expires_at: datetime | None = None,
) -> PermissionRule:
    """Factory for creating a new ``PermissionRule`` with the current UTC timestamp.

    Convenience wrapper for pipeline and CLI code.

    Args:
        tool_id: Canonical adapter identifier.
        decision: Tri-state decision.
        scope: Rule scope.
        mode: The ``PermissionMode`` active when the rule is created.
        expires_at: Optional expiry timestamp (UTC tz-aware).

    Returns:
        A new frozen ``PermissionRule`` instance.
    """
    return PermissionRule(
        tool_id=tool_id,
        decision=decision,
        scope=scope,
        created_at=datetime.now(tz=UTC),
        created_by_mode=mode,
        expires_at=expires_at,
    )
