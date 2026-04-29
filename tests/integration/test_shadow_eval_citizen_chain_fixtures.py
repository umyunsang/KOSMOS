# SPDX-License-Identifier: Apache-2.0
"""T004 (Epic η #2298) — Validate the 5 new shadow-eval fixtures load without error
and respect the cross-field invariants documented in
specs/2298-system-prompt-rewrite/contracts/shadow-eval-fixture-schema.md.

This test gates FR-015 + SC-004.
"""

import json
from pathlib import Path

import pytest

from tests.fixtures.shadow_eval.citizen_chain._schema import CitizenChainFixture

_FIXTURE_DIR = Path("tests/fixtures/shadow_eval/citizen_chain")

_ACTIVE_FAMILIES: frozenset[str] = frozenset(
    {
        "gongdong_injeungseo",
        "geumyung_injeungseo",
        "ganpyeon_injeung",
        "mobile_id",
        "mydata",
        "simple_auth_module",
        "modid",
        "kec",
        "geumyung_module",
        "any_id_sso",
    }
)


@pytest.mark.parametrize("fixture_path", sorted(_FIXTURE_DIR.glob("*.json")))
def test_fixture_loads_and_satisfies_invariants(fixture_path: Path) -> None:
    """Each fixture JSON must load without ValidationError and pass cross-field invariants."""
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture = CitizenChainFixture.model_validate(raw)

    if fixture.expected_first_tool_call.name == "verify":
        assert fixture.expected_family_hint is not None, (
            f"{fixture_path.name}: verify call requires expected_family_hint to be non-None"
        )
        assert fixture.expected_family_hint == fixture.expected_first_tool_call.arguments.get(
            "family_hint"
        ), f"{fixture_path.name}: expected_family_hint must match arguments['family_hint']"
        assert fixture.expected_family_hint in _ACTIVE_FAMILIES, (
            f"{fixture_path.name}: expected_family_hint '{fixture.expected_family_hint}' "
            f"not in _ACTIVE_FAMILIES"
        )
        assert fixture.expected_family_hint != "digital_onepass", (
            f"{fixture_path.name}: digital_onepass is forbidden (FR-002)"
        )


def test_fixture_count_matches_epic_target() -> None:
    """FR-015: exactly 5 new fixtures at the citizen_chain root.

    NOTE: This test FAILS until Phase 4 (T013–T017) creates the 5 fixture JSON files.
    That is BY DESIGN — this test documents the contract and will pass once the
    fixtures are authored.
    """
    json_files = sorted(p for p in _FIXTURE_DIR.iterdir() if p.is_file() and p.suffix == ".json")
    assert len(json_files) == 5, (
        f"Expected 5 new fixtures (FR-015), found {len(json_files)}: {[p.name for p in json_files]}"
    )
