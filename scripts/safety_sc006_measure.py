# SPDX-License-Identifier: Apache-2.0
"""SC-006 cache-prefix stability measurement.

Assembles two fresh system prompts with identical ``SystemPromptConfig``
instances and asserts the prefix up to (but not including) § 5 (session
guidance) is byte-identical between the two calls.  Records the prefix
byte length and SHA-256 digest for the PR-B body.

Usage::

    uv run python scripts/safety_sc006_measure.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from kosmos.context.models import SystemPromptConfig  # noqa: E402
from kosmos.context.system_prompt import SystemPromptAssembler  # noqa: E402


def _prefix_through_section_4(assembler: SystemPromptAssembler, cfg: SystemPromptConfig) -> str:
    sections = [
        assembler._platform_identity_section(cfg),
        assembler._language_policy_section(cfg),
        assembler._tool_use_policy_section(),
        assembler._trust_hierarchy_section(),
    ]
    if cfg.personal_data_warning:
        sections.append(assembler._personal_data_reminder_section())
    return "\n\n".join(sections)


def _measure(cfg: SystemPromptConfig, label: str) -> str:
    a1 = SystemPromptAssembler()
    a2 = SystemPromptAssembler()
    p1 = _prefix_through_section_4(a1, cfg)
    p2 = _prefix_through_section_4(a2, cfg)
    full = a1.assemble(cfg)
    assert p1 == p2, f"{label}: prefix drift between two assembler instances"
    assert full.startswith(p1), f"{label}: full prompt does not begin with prefix"
    digest = hashlib.sha256(p1.encode("utf-8")).hexdigest()
    print(f"{label}: bytes={len(p1)} sha256={digest}")
    print(f"{label}: full bytes={len(full)} suffix bytes={len(full) - len(p1)}")
    return digest


def main() -> int:
    print("SC-006 measurement — cache-prefix byte-identical stability")
    d1 = _measure(SystemPromptConfig(), "default  ")
    d2 = _measure(SystemPromptConfig(personal_data_warning=True), "pdw=True ")
    print("\nResult: prefix §1–§4 (incl. §3a trust hierarchy) is stable across "
          "assembler instantiations.")
    print(f"  default  SHA-256: {d1}")
    print(f"  pdw=True SHA-256: {d2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
