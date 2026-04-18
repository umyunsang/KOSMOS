# SPDX-License-Identifier: Apache-2.0
"""T073 — Docs-lint test: security spec v1.2 structural assertions.

Asserts that ``docs/security/tool-template-security-spec-v1.md`` has been
correctly bumped to v1.2 per Spec 031 US6 (FR-027, FR-029, SC-007):

1. Contains a Version 1.2 marker in the metadata header or a heading
   that makes v1.2 promotion explicit.
2. Contains a migration note section that references both the v1.1 source
   version and the v1.2 target version (case-insensitive match).
3. Does NOT contain the legacy ``TOOL_MIN_AAL`` single-axis table section —
   specifically, the ``## 2. `TOOL_MIN_AAL` Table`` section heading and its
   8-verb body rows MUST be absent. (The phrase ``TOOL_MIN_AAL`` may still
   appear in migration-note *prose* describing what was removed; the check
   is scoped to the normative section heading pattern.)
4. Contains the dual-axis ``(published_tier_minimum, nist_aal_hint)`` table —
   both column header strings must appear within a 500-character window,
   indicating they are part of the same table region.

Expected state while Teammate B has not yet landed the doc edits: ALL four
assertions FAIL (TDD red phase). Once the doc is bumped to v1.2, all four
should turn green.

References:
- specs/031-five-primitive-harness/spec.md FR-027, FR-029, SC-007
- specs/031-five-primitive-harness/tasks.md T073
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parents[2]
_SPEC_DOC = _REPO_ROOT / "docs" / "security" / "tool-template-security-spec-v1.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_doc() -> str:
    """Read the security spec document; skip all tests if it is missing."""
    if not _SPEC_DOC.exists():
        pytest.skip(f"Security spec doc not found: {_SPEC_DOC}")
    return _SPEC_DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Assertion 1 — Version 1.2 marker present
# ---------------------------------------------------------------------------

_V12_MARKER_RE = re.compile(
    r"""
    (?:
        Version\s*:\s*1\.2          # YAML-ish metadata: "Version: 1.2"
        |
        \bv1\.2\b                   # heading containing v1.2 token
        |
        Version\s+1\.2              # prose variant: "Version 1.2"
        |
        \#.*1\.2                    # any heading containing 1.2
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def test_doc_contains_version_12_marker() -> None:
    """Assert the doc metadata or a heading explicitly marks v1.2 (FR-027).

    RED until Teammate B bumps the header to ``Version: 1.2``.
    """
    content = _read_doc()
    assert _V12_MARKER_RE.search(content) is not None, (
        f"docs/security/tool-template-security-spec-v1.md does not contain a "
        f"v1.2 version marker. Expected one of: 'Version: 1.2', a heading "
        f"containing 'v1.2', or 'Version 1.2'. "
        f"Land the doc bump (T076) to fix this."
    )


# ---------------------------------------------------------------------------
# Assertion 2 — Migration note section references v1.1 → v1.2 transition
# ---------------------------------------------------------------------------

# The migration note must contain the word "migration" (case-insensitive)
# AND either "v1.1" or "1.1" to establish which version is being superseded,
# AND either "v1.2" or "1.2" to establish the target version.
_MIGRATION_WORD_RE = re.compile(r"\bmigration\b", re.IGNORECASE)
_V11_REF_RE = re.compile(r"\bv?1\.1\b", re.IGNORECASE)
_V12_REF_RE = re.compile(r"\bv?1\.2\b", re.IGNORECASE)


def test_doc_contains_migration_note_section() -> None:
    """Assert a migration note mentioning both v1.1 and v1.2 is present (FR-029).

    RED until T078 writes the v1.1 → v1.2 migration note.
    """
    content = _read_doc()

    has_migration = _MIGRATION_WORD_RE.search(content) is not None
    has_v11 = _V11_REF_RE.search(content) is not None
    has_v12 = _V12_REF_RE.search(content) is not None

    assert has_migration, (
        "No 'migration' heading/section found in "
        "docs/security/tool-template-security-spec-v1.md. "
        "T078 must add a 'v1.1 → v1.2 Migration Note' section."
    )
    assert has_v11, (
        "Migration note must explicitly reference v1.1 (the superseded version). "
        "T078 must mention '1.1' or 'v1.1' in the migration section."
    )
    assert has_v12, (
        "Migration note must explicitly reference v1.2 (the target version). "
        "T078 must mention '1.2' or 'v1.2' in the migration section."
    )


# ---------------------------------------------------------------------------
# Assertion 3 — Legacy TOOL_MIN_AAL normative section heading is ABSENT
# ---------------------------------------------------------------------------

# Match the normative section heading pattern from the current v1.1 doc:
#   ## 2. `TOOL_MIN_AAL` Table
# and also its 8-verb body rows (at least one row containing a legacy verb).
# We intentionally do NOT forbid "TOOL_MIN_AAL" in prose — migration notes
# may reference it by name when describing what was removed. The check is
# narrow: the *section heading* pattern must be gone.
_TOOL_MIN_AAL_HEADING_RE = re.compile(
    r"^#{1,4}\s+\d*\.?\s*`?TOOL_MIN_AAL`?\s+[Tt]able",
    re.MULTILINE,
)

# The 8 legacy verb rows that should be removed from the body table.
_LEGACY_VERB_TABLE_ROWS = [
    "check_eligibility",
    "subscribe_alert",
    "reserve_slot",
    "issue_certificate",
    "submit_application",
]


def test_doc_does_not_contain_tool_min_aal_section_heading() -> None:
    """Assert the TOOL_MIN_AAL normative section heading is absent (FR-027 / T077).

    The heading ``## 2. `TOOL_MIN_AAL` Table`` (and variants) MUST be gone.
    Prose references to TOOL_MIN_AAL in migration notes are permitted.

    RED until T077 replaces the section with the dual-axis table.
    """
    content = _read_doc()
    match = _TOOL_MIN_AAL_HEADING_RE.search(content)
    assert match is None, (
        f"Legacy TOOL_MIN_AAL section heading still present at position "
        f"{match.start() if match else 0}: "
        f"{content[match.start():match.start() + 60]!r}. "
        "T077 must replace this section with the dual-axis table."
    )


def test_doc_does_not_contain_legacy_verb_body_rows_in_normative_table() -> None:
    """Assert legacy 8-verb rows no longer appear in a normative table block (FR-027 / T077).

    We detect table rows by the Markdown pipe ``|`` prefix combined with one of
    the legacy tool IDs surrounded by backticks. This pattern is specific enough
    to table cells and won't fire on migration-note prose.

    RED until T077 removes the 8-verb body rows.
    """
    content = _read_doc()
    for verb in _LEGACY_VERB_TABLE_ROWS:
        # Matches a markdown table row containing the verb in a code span: | `<verb>` |
        pattern = re.compile(
            rf"\|\s*`{re.escape(verb)}`\s*\|",
            re.MULTILINE,
        )
        match = pattern.search(content)
        assert match is None, (
            f"Legacy verb {verb!r} still appears in a normative table row at "
            f"position {match.start() if match else 0}. "
            "T077 must replace the TOOL_MIN_AAL 8-verb table body with the "
            "dual-axis (published_tier_minimum, nist_aal_hint) table."
        )


# ---------------------------------------------------------------------------
# Assertion 4 — Dual-axis table present
# ---------------------------------------------------------------------------

# Both column header strings must appear in the document and within a
# 500-character window of each other (same table region heuristic).
_TIER_COL = "published_tier_minimum"
_AAL_COL = "nist_aal_hint"
_DUAL_AXIS_PROXIMITY = 500  # characters


def test_doc_contains_dual_axis_table() -> None:
    """Assert both dual-axis column headers appear in close proximity (SC-007 / FR-027).

    Both ``published_tier_minimum`` and ``nist_aal_hint`` must appear within
    {_DUAL_AXIS_PROXIMITY} characters of each other, indicating they are
    co-located in the same table region.

    RED until T077 writes the dual-axis table into the doc.
    """
    content = _read_doc()

    tier_pos = content.find(_TIER_COL)
    aal_pos = content.find(_AAL_COL)

    assert tier_pos != -1, (
        f"Column header {_TIER_COL!r} not found in "
        "docs/security/tool-template-security-spec-v1.md. "
        "T077 must add the dual-axis table."
    )
    assert aal_pos != -1, (
        f"Column header {_AAL_COL!r} not found in "
        "docs/security/tool-template-security-spec-v1.md. "
        "T077 must add the dual-axis table."
    )

    distance = abs(tier_pos - aal_pos)
    assert distance <= _DUAL_AXIS_PROXIMITY, (
        f"Column headers {_TIER_COL!r} (pos {tier_pos}) and "
        f"{_AAL_COL!r} (pos {aal_pos}) are {distance} chars apart "
        f"(threshold: {_DUAL_AXIS_PROXIMITY}). "
        "They must appear in the same table region. "
        "T077 must place both columns in a single dual-axis table."
    )
