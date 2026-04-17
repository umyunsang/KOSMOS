# SPDX-License-Identifier: Apache-2.0
"""Refactor equivalence tests for Epic #467 Phase 3.2 (T013).

RED phase: these tests are authored BEFORE the prompt files and PromptLoader exist
(Phase 3.3 creates them). Both tests are expected to fail until Phase 3.3 lands.

Two test cases:
  1. test_assemble_matches_pre_refactor_golden — asserts that
     SystemPromptAssembler.assemble(SystemPromptConfig()) output, after applying
     the FR-X03 correction (address_to_region -> resolve_location) to the
     pre-refactor golden, equals the post-refactor assembled output.  This
     validates byte-level equivalence modulo the single documented correction.

  2. test_session_guidance_v1_matches_expected_fixture — loads
     prompts/session_guidance_v1.md from disk and asserts its bytes equal
     tests/context/fixtures/session_guidance_v1_expected.txt, directly
     verifying that the FR-X03 correction is applied in the prompt file.
     Fails RED until prompts/session_guidance_v1.md is created (Phase 3.3).

Hard rules (AGENTS.md):
  - Bytes comparison; UTF-8 encoding assumed; .read_bytes() used throughout.
  - pathlib.Path for all filesystem access; absolute paths resolved from __file__.
  - No Korean in test strings or identifiers.
"""

from __future__ import annotations

import pathlib

import pytest

from kosmos.context.models import SystemPromptConfig
from kosmos.context.system_prompt import SystemPromptAssembler

# ---------------------------------------------------------------------------
# Path constants — all absolute, resolved from this file's location.
# ---------------------------------------------------------------------------
_TESTS_CONTEXT_DIR = pathlib.Path(__file__).parent
_FIXTURES_DIR = _TESTS_CONTEXT_DIR / "fixtures"

_PRE_REFACTOR_GOLDEN = _FIXTURES_DIR / "system_prompt_pre_refactor.txt"
_SESSION_GUIDANCE_EXPECTED = _FIXTURES_DIR / "session_guidance_v1_expected.txt"

# prompts/ directory is at repo root — two levels above tests/context/
_REPO_ROOT = _TESTS_CONTEXT_DIR.parent.parent
_PROMPTS_DIR = _REPO_ROOT / "prompts"
_SESSION_GUIDANCE_V1_MD = _PROMPTS_DIR / "session_guidance_v1.md"

# FR-X03 documented correction: old tool name -> new tool name.
_FR_X03_OLD = b"address_to_region"
_FR_X03_NEW = b"resolve_location"


class TestSystemPromptRefactorEquivalence:
    """Byte-level equivalence between pre-refactor golden and post-refactor output.

    Phase 3.2 RED tests — both cases fail until Phase 3.3 delivers the prompt
    files and PromptLoader integration.
    """

    def test_assemble_matches_pre_refactor_golden(self) -> None:
        """Assembled output equals pre-refactor golden modulo the FR-X03 correction.

        Strategy: apply resolve_location substitution to the pre-refactor golden
        bytes, then compare against the live assembled output (also encoded as
        UTF-8 bytes).  This asserts byte-identical equivalence with the single
        documented FR-X03 correction and nothing else.

        This test will turn GREEN once Phase 3.3 refactors SystemPromptAssembler
        to load from prompts/system_v1.md and prompts/session_guidance_v1.md,
        because the loaded content will carry the resolve_location correction.
        """
        golden_bytes = _PRE_REFACTOR_GOLDEN.read_bytes()
        # Apply the FR-X03 correction to the golden to produce the expected
        # post-refactor bytes.  The assembled output must match this exactly.
        expected_bytes = golden_bytes.replace(_FR_X03_OLD, _FR_X03_NEW)

        assembler = SystemPromptAssembler()
        assembled = assembler.assemble(SystemPromptConfig())
        assembled_bytes = assembled.encode("utf-8")

        assert assembled_bytes == expected_bytes, (
            "Post-refactor assembled output does not match pre-refactor golden "
            "after applying FR-X03 correction (address_to_region -> resolve_location). "
            "Diff: assembled has "
            f"{len(assembled_bytes)} bytes, expected {len(expected_bytes)} bytes."
        )

    def test_session_guidance_v1_matches_expected_fixture(self) -> None:
        """prompts/session_guidance_v1.md bytes equal session_guidance_v1_expected.txt.

        Directly asserts FR-X03: the v1 prompt file on disk must contain
        resolve_location (not address_to_region).

        FAILS RED until Phase 3.3 creates prompts/session_guidance_v1.md.
        """
        if not _SESSION_GUIDANCE_V1_MD.exists():
            pytest.fail(
                f"prompts/session_guidance_v1.md not found at {_SESSION_GUIDANCE_V1_MD}. "
                "Phase 3.3 must create this file before this test can pass. "
                "This is the expected RED state for Phase 3.2."
            )

        actual_bytes = _SESSION_GUIDANCE_V1_MD.read_bytes()
        expected_bytes = _SESSION_GUIDANCE_EXPECTED.read_bytes()

        assert actual_bytes == expected_bytes, (
            "prompts/session_guidance_v1.md does not match "
            "tests/context/fixtures/session_guidance_v1_expected.txt. "
            "Ensure the FR-X03 correction (resolve_location) is applied and "
            "no extra whitespace or encoding differences exist."
        )
