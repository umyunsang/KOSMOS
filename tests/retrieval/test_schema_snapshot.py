# SPDX-License-Identifier: Apache-2.0
"""Frozen-contract schema snapshot regression gate (spec 026, FR-003 / SC-04).

Appendix B of ``specs/026-retrieval-dense-embeddings/spec.md`` fixes the
JSON schemas of ``LookupSearchInput``, ``LookupSearchResult``, and
``AdapterCandidate`` at byte level. This test asserts the live pydantic
models round-trip to the committed snapshot verbatim.  Any drift —
field reorder, default change, description edit — fails the build.

Snapshot authorship (T012):
    uv run python -c "from kosmos.tools.models import ...; json.dumps(
        model_json_schema(), indent=2, sort_keys=True, ensure_ascii=False
    )"
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kosmos.tools.models import AdapterCandidate, LookupSearchInput, LookupSearchResult

_SNAPSHOT_DIR = Path(__file__).parent / "__snapshots__"


_CASES: list[tuple[str, type]] = [
    ("lookup_search_input.schema.json", LookupSearchInput),
    ("lookup_search_result.schema.json", LookupSearchResult),
    ("adapter_candidate.schema.json", AdapterCandidate),
]


@pytest.mark.parametrize(("filename", "model"), _CASES, ids=[f for f, _ in _CASES])
def test_schema_matches_snapshot(filename: str, model: type) -> None:
    """Live ``model_json_schema()`` MUST equal the committed snapshot.

    Serialisation parameters MUST match the T012 authoring command
    (``indent=2, sort_keys=True, ensure_ascii=False`` + trailing newline)
    so the comparison is byte-exact.
    """
    snapshot_path = _SNAPSHOT_DIR / filename
    assert snapshot_path.exists(), (
        f"Missing snapshot {filename}. Regenerate with T012 command "
        "before committing schema-impacting changes."
    )

    expected = snapshot_path.read_text(encoding="utf-8")
    actual = (
        json.dumps(
            model.model_json_schema(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )

    assert actual == expected, (
        f"Schema drift detected for {model.__name__}. "
        f"Snapshot {snapshot_path} is byte-frozen per FR-003 / SC-04. "
        "If the drift is intentional (Epic #507 contract change), "
        "regenerate the snapshot via T012 AND update the SHA-256 values "
        "recorded in specs/026-retrieval-dense-embeddings/plan.md § "
        "Appendix B."
    )
