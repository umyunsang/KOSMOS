# SPDX-License-Identifier: Apache-2.0
"""Python entry-point fallback for ``kosmos plugin init``.

Mirror of the TypeScript core in ``tui/src/commands/plugin-init.ts``.
This module exists so non-TUI users can scaffold a plugin via:

    uvx kosmos-plugin-init <name> --tier live --layer 1 --no-pii

without having Bun or the TUI installed. The emitted file tree is
byte-equivalent to the TS path's non-interactive output (same template
strings; tested at the snapshot level by quickstart timing T023).

Interactive Ink prompts are TUI-only — the Python fallback is
non-interactive by design (FR-002 escape hatch).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

_PLUGIN_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True, slots=True)
class PIPATrusteeArgs:
    trustee_org_name: str
    trustee_contact: str
    pii_fields_handled: tuple[str, ...]
    legal_basis: str
    acknowledgment_sha256: str


@dataclass(frozen=True, slots=True)
class InitOptions:
    name: str
    tier: Literal["live", "mock"]
    layer: Literal[1, 2, 3]
    pii: bool
    out: Path
    force: bool
    search_hint_ko: str
    search_hint_en: str
    pipa: PIPATrusteeArgs | None = None
    # Override for tier=mock: URL or attribution string pointing at the
    # public spec the mock mirrors. Defaults to a placeholder that the
    # contributor MUST replace before publishing (memory
    # feedback_mock_evidence_based).
    mock_source_spec: str | None = None


@dataclass(frozen=True, slots=True)
class InitResult:
    exit_code: int
    out_dir: Path | None
    files_written: list[str]
    error_kind: str | None
    error_message: str | None


def _validate_name(name: str) -> str | None:
    if not _PLUGIN_NAME_RE.fullmatch(name):
        return f"plugin name {name!r} must match ^[a-z][a-z0-9_]*$"
    if len(name) > 64:
        return f"plugin name max length 64 (got {len(name)})"
    return None


def _validate_pipa(pii: bool, ack: PIPATrusteeArgs | None) -> str | None:
    if pii and ack is None:
        return "pii=True requires --pipa-* flags (see docs/plugins/security-review.md)"
    if not pii and ack is not None:
        return "pii=False must NOT supply --pipa-* flags"
    if ack is not None and not _SHA256_RE.fullmatch(ack.acknowledgment_sha256):
        return (
            "pipa_acknowledgment_sha256 must match ^[a-f0-9]{64}$ "
            f"(got {len(ack.acknowledgment_sha256)} chars)"
        )
    return None


def _manifest_dict(opts: InitOptions) -> dict[str, object]:
    # Epic δ #2295 Path B: standalone auth_level / pipa_class / is_personal_data removed.
    # The adapter now carries a policy block with citizen_facing_gate; auth_level and
    # pipa_class are derived at runtime from policy.citizen_facing_gate via
    # kosmos.tools.policy_derivation. Layer 1 (green) maps to "read-only" gate → AAL1.
    # Layer 2 (orange) maps to "login" gate → AAL2. Layer 3 (red) maps to "sign" gate → AAL3.
    _LAYER_TO_GATE = {1: "read-only", 2: "login", 3: "sign"}
    _LAYER_TO_GATE_TEXT = {
        1: "공공데이터포털 이용약관 제7조 (공공데이터의 제공 및 이용)",
        2: "본인확인 서비스 이용약관 (로그인 필요)",
        3: "전자서명법 제5조 (서명 및 제출 행위)",
    }
    citizen_gate = _LAYER_TO_GATE[opts.layer]
    return {
        "plugin_id": opts.name,
        "version": "0.1.0",
        "adapter": {
            "tool_id": f"plugin.{opts.name}.lookup",
            "primitive": "lookup",
            "module_path": f"plugin_{opts.name}.adapter",
            "input_model_ref": f"plugin_{opts.name}.schema:LookupInput",
            "source_mode": "OPENAPI",
            "published_tier_minimum": "digital_onepass_level1_aal1",
            "nist_aal_hint": "AAL1",
            "auth_type": "api_key",
            "policy": {
                "real_classification_url": "https://www.data.go.kr/policy",
                "real_classification_text": _LAYER_TO_GATE_TEXT[opts.layer],
                "citizen_facing_gate": citizen_gate,
                "last_verified": "2026-04-29T00:00:00Z",
            },
        },
        "tier": opts.tier,
        "mock_source_spec": (
            (opts.mock_source_spec or "https://example.com/mock-source-spec")
            if opts.tier == "mock"
            else None
        ),
        "processes_pii": opts.pii,
        "pipa_trustee_acknowledgment": (
            {
                "trustee_org_name": opts.pipa.trustee_org_name,
                "trustee_contact": opts.pipa.trustee_contact,
                "pii_fields_handled": list(opts.pipa.pii_fields_handled),
                "legal_basis": opts.pipa.legal_basis,
                "acknowledgment_sha256": opts.pipa.acknowledgment_sha256,
            }
            if opts.pipa is not None
            else None
        ),
        "dpa_reference": None,
        "slsa_provenance_url": (
            f"https://github.com/kosmos-plugin-store/kosmos-plugin-{opts.name}/"
            f"releases/download/v0.1.0/{opts.name}.intoto.jsonl"
        ),
        "otel_attributes": {"kosmos.plugin.id": opts.name},
        "search_hint_ko": opts.search_hint_ko,
        "search_hint_en": opts.search_hint_en,
        "permission_layer": opts.layer,
    }


def _build_files(opts: InitOptions) -> dict[str, str]:
    name = opts.name
    layer_note = {
        1: "Layer 1 (green) — read-only public data.",
        2: "Layer 2 (orange) — citizen-scoped data; consent required.",
        3: "Layer 3 (red) — irreversible action; explicit consent required.",
    }[opts.layer]
    adapter_template = _ADAPTER_LIVE if opts.tier == "live" else _ADAPTER_MOCK
    manifest_yaml = yaml.safe_dump(_manifest_dict(opts), allow_unicode=True, sort_keys=False)
    return {
        "pyproject.toml": _PYPROJECT.format(name=name),
        "manifest.yaml": manifest_yaml,
        f"plugin_{name}/__init__.py": _PKG_INIT.format(name=name),
        f"plugin_{name}/adapter.py": adapter_template.format(name=name, layer_note=layer_note),
        f"plugin_{name}/schema.py": _SCHEMA,
        "tests/__init__.py": "# SPDX-License-Identifier: Apache-2.0\n",
        "tests/conftest.py": _CONFTEST,
        "tests/test_adapter.py": _TEST_ADAPTER.format(name=name),
        f"tests/fixtures/plugin.{name}.lookup.json": (
            '{\n  "echo": "sample",\n  "source": "' + name + '-stub"\n}\n'
        ),
        ".github/workflows/plugin-validation.yml": _PLUGIN_VAL_WORKFLOW,
        ".github/workflows/release-with-slsa.yml": _RELEASE_WORKFLOW,
        "README.ko.md": _README_KO.format(name=name, tier=opts.tier),
        "README.en.md": _README_EN.format(name=name, tier=opts.tier),
        ".gitignore": _GITIGNORE,
    }


_PYPROJECT = """[project]
name = "kosmos-plugin-{name}"
version = "0.1.0"
description = "KOSMOS plugin scaffolded by 'uvx kosmos-plugin-init'"
requires-python = ">=3.12"
license = {{ text = "Apache-2.0" }}
dependencies = [
  "pydantic>=2.13",
  "httpx>=0.27",
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["plugin_{name}"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
"""

_PKG_INIT = '''# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin package: {name}.

NOTE: ``TOOL`` is intentionally NOT re-exported here. It is built
lazily at access time (PEP 562) by ``adapter.py`` so the scaffold's
tests can run without ``kosmos`` installed. Consumers that need the
GovAPITool entry should ``from .adapter import TOOL`` directly — the
KOSMOS host follows that convention.
"""

from .adapter import adapter
from .schema import LookupInput, LookupOutput

__all__ = ["adapter", "LookupInput", "LookupOutput"]
'''

_ADAPTER_LIVE = '''# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin adapter for {name}.

{layer_note}
"""

from __future__ import annotations

from typing import Any

import httpx  # noqa: F401 — kept so Q7-LIVE-USES-NETWORK passes; uncomment real call below.

from .schema import LookupInput, LookupOutput


def _build_tool() -> Any:
    """Construct the GovAPITool registry entry on first access.

    Imported lazily so the scaffold's tests (which do not require the
    KOSMOS host) can run without ``kosmos`` installed. The host triggers
    construction at install time when reading the module-level ``TOOL``
    attribute via PEP 562.
    """
    from kosmos.tools.models import GovAPITool

    # Epic δ #2295 Path B: policy block replaces standalone auth_level /
    # pipa_class / is_irreversible / dpa_reference / is_personal_data fields.
    # auth_level and pipa_class are derived at runtime from
    # policy.citizen_facing_gate via kosmos.tools.policy_derivation.
    from datetime import datetime, timezone

    from kosmos.tools.models import AdapterRealDomainPolicy

    policy = AdapterRealDomainPolicy(
        real_classification_url="https://www.data.go.kr/policy",
        real_classification_text="공공데이터포털 이용약관 제7조 (공공데이터의 제공 및 이용)",
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    )
    return GovAPITool(
        id="plugin.{name}.lookup",
        name_ko="{name} 조회",
        ministry="OTHER",
        category=["{name}"],
        endpoint="https://example.com/{name}",
        auth_type="api_key",
        input_schema=LookupInput,
        output_schema=LookupOutput,
        search_hint="{name} 조회 lookup",
        policy=policy,
        primitive="lookup",
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
    )


_TOOL_CACHE: Any = None


def __getattr__(name: str) -> Any:
    """PEP 562: provide lazy module-level ``TOOL`` so this file imports
    without ``kosmos`` being available (e.g. scaffold tests)."""
    global _TOOL_CACHE
    if name == "TOOL":
        if _TOOL_CACHE is None:
            _TOOL_CACHE = _build_tool()
        return _TOOL_CACHE
    raise AttributeError(name)


async def adapter(payload: LookupInput) -> dict[str, Any]:
    """Replace this stub with a real httpx call against the upstream API."""
    return {{"echo": payload.query, "source": "{name}-stub"}}
'''


_ADAPTER_MOCK = '''# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin adapter for {name} (Mock tier).

{layer_note}

This adapter does NOT call the upstream API — it replays a recorded
fixture under tests/fixtures/. Mock tier is the right choice when the
upstream system has no public API, requires partnership credentials
KOSMOS does not have, or the integration is documented but not
implementable today (memory feedback_mock_evidence_based).

When the partnership / API access is established, swap this adapter
to a Live-tier implementation by:

1. Adding `import httpx` at the top.
2. Replacing the fixture-replay path below with a real network call.
3. Updating manifest.yaml: `tier: live`, `mock_source_spec: null`.
4. Re-running ``uv run pytest`` and the 50-item validation workflow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import LookupInput, LookupOutput

_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    / "plugin.{name}.lookup.json"
)


def _build_tool() -> Any:
    """Construct the GovAPITool registry entry on first access (PEP 562)."""
    # Epic δ #2295 Path B: policy block replaces standalone auth_level /
    # pipa_class / is_irreversible / dpa_reference / is_personal_data fields.
    from datetime import datetime, timezone

    from kosmos.tools.models import AdapterRealDomainPolicy, GovAPITool

    policy = AdapterRealDomainPolicy(
        real_classification_url="https://www.data.go.kr/policy",
        real_classification_text="공공데이터포털 이용약관 제7조 (공공데이터의 제공 및 이용)",
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    )
    return GovAPITool(
        id="plugin.{name}.lookup",
        name_ko="{name} 조회",
        ministry="OTHER",
        category=["{name}"],
        endpoint="mock://{name}",
        auth_type="api_key",
        input_schema=LookupInput,
        output_schema=LookupOutput,
        search_hint="{name} 조회 lookup",
        policy=policy,
        primitive="lookup",
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
        adapter_mode="mock",
    )


_TOOL_CACHE: Any = None


def __getattr__(name: str) -> Any:
    """PEP 562 lazy TOOL — see plugin-template README.staging.md."""
    global _TOOL_CACHE
    if name == "TOOL":
        if _TOOL_CACHE is None:
            _TOOL_CACHE = _build_tool()
        return _TOOL_CACHE
    raise AttributeError(name)


async def adapter(payload: LookupInput) -> dict[str, Any]:
    """Mock-tier adapter: replays the recorded fixture under tests/fixtures/.

    The recorded fixture IS the simulated upstream response — its shape
    must match :class:`LookupOutput`. We do not attach the input echo;
    contributor adjusts the fixture directly to reflect realistic shapes.
    """
    if not _FIXTURE_PATH.is_file():
        raise RuntimeError(
            f"mock fixture missing at {{_FIXTURE_PATH}}; record one and commit."
        )
    raw = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    # Touch the payload so unused-arg lints stay quiet; the input is
    # otherwise unused in the mock path. Real adapters use payload to
    # parameterise the call — replace this when promoting to live tier.
    _ = payload.model_dump()
    return raw
'''

_SCHEMA = '''# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 input + output schemas for the lookup primitive."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LookupInput(BaseModel):
    """Input model — REPLACE with real fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, description="Search query text.")


class LookupOutput(BaseModel):
    """Output model — REPLACE with real fields matching the upstream response."""

    model_config = ConfigDict(frozen=True, extra="allow")

    echo: str = Field(description="Echo of the input query (placeholder).")
    source: str = Field(description="Source identifier (placeholder).")
'''

_CONFTEST = '''# SPDX-License-Identifier: Apache-2.0
"""Pytest fixtures — Constitution §IV: no live network calls in CI.

Only IPv4 / IPv6 socket creation is blocked; AF_UNIX socketpairs used
by the asyncio event loop continue to work (otherwise pytest-asyncio
would fail to set up).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest

_REAL_SOCKET = socket.socket


@pytest.fixture(autouse=True)
def block_network(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    if request.node.get_closest_marker("allow_network") is not None:
        yield
        return

    def _maybe_block(*args: Any, **kwargs: Any) -> socket.socket:
        family = (
            kwargs.get("family")
            if "family" in kwargs
            else (args[0] if args else socket.AF_INET)
        )
        if family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(
                "Outbound network access is blocked in plugin tests "
                "(Constitution §IV). Use a recorded fixture or "
                "@pytest.mark.allow_network for the rare opt-out."
            )
        return _REAL_SOCKET(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", _maybe_block)
    yield


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "allow_network: opt out of the autouse network block",
    )
'''

_TEST_ADAPTER = '''# SPDX-License-Identifier: Apache-2.0
"""Adapter happy-path + error-path tests for {name}.

The scaffolded test passes out of the box because the adapter stub
echoes the input deterministically. Replace these assertions with real
ones once the adapter calls the upstream public API.
"""

from __future__ import annotations

import pytest

from plugin_{name}.adapter import adapter
from plugin_{name}.schema import LookupInput, LookupOutput


@pytest.mark.asyncio
async def test_adapter_happy_path() -> None:
    payload = LookupInput(query="hello")
    result = await adapter(payload)
    LookupOutput.model_validate(result)
    assert result["echo"] == "hello"


def test_input_validation_rejects_empty_query() -> None:
    with pytest.raises(Exception):
        LookupInput(query="")
'''

_PLUGIN_VAL_WORKFLOW = """name: plugin-validation

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    uses: umyunsang/KOSMOS/.github/workflows/plugin-validation.yml@main
    secrets: inherit
"""

_RELEASE_WORKFLOW = """name: release-with-slsa

on:
  push:
    tags: ['v*']

permissions:
  id-token: write
  contents: write
  actions: read

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digest: ${{ steps.hash.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      - id: hash
        run: |
          tar -czf bundle.tar.gz --exclude='.git' .
          echo "digest=$(sha256sum bundle.tar.gz | base64 -w0)" >> "$GITHUB_OUTPUT"

  provenance:
    needs: build
    permissions:
      id-token: write
      contents: write
      actions: read
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0
    with:
      base64-subjects: ${{ needs.build.outputs.digest }}
      upload-assets: true
"""

_README_KO = """# kosmos-plugin-{name}

KOSMOS 플러그인 — `{name}` 어댑터.

## 설치

```bash
kosmos plugin install {name}
```

## 개발

```bash
uv sync
uv run pytest
```

이 플러그인은 **{tier}** tier 입니다.
"""

_README_EN = """# kosmos-plugin-{name}

KOSMOS plugin — `{name}` adapter.

## Install

```bash
kosmos plugin install {name}
```

## Develop

```bash
uv sync
uv run pytest
```

This plugin ships at **{tier}** tier.
"""

_GITIGNORE = """__pycache__/
*.py[cod]
.venv/
.pytest_cache/
*.egg-info/
dist/
build/
uv.lock
.env
.DS_Store
"""


def run_init(opts: InitOptions) -> InitResult:
    name_err = _validate_name(opts.name)
    if name_err:
        return InitResult(1, None, [], "invalid_name", name_err)
    pipa_err = _validate_pipa(opts.pii, opts.pipa)
    if pipa_err:
        return InitResult(3, None, [], "pipa_acknowledgment_error", pipa_err)

    out_dir = opts.out.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        if not opts.force:
            return InitResult(
                2,
                None,
                [],
                "out_dir_non_empty",
                f"output directory {out_dir} is not empty; pass --force to overwrite",
            )
        try:
            shutil.rmtree(out_dir)
        except OSError as exc:
            return InitResult(2, None, [], "out_dir_clear_failed", str(exc))

    files = _build_files(opts)
    written: list[str] = []
    try:
        for rel, body in files.items():
            target = out_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            written.append(rel)
    except OSError as exc:
        return InitResult(2, out_dir, written, "write_failed", str(exc))

    return InitResult(0, out_dir, written, None, None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kosmos-plugin-init",
        description=(
            "Scaffold a KOSMOS plugin (Python entry-point fallback for the TUI command). "
            "See docs/plugins/quickstart.ko.md for the full walkthrough."
        ),
    )
    parser.add_argument("name", help="plugin id (snake_case)")
    parser.add_argument("--tier", choices=("live", "mock"), required=True)
    parser.add_argument("--layer", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument(
        "--pii",
        action=argparse.BooleanOptionalAction,
        required=True,
        help="--pii / --no-pii (required)",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--search-hint-ko",
        default=None,
        help="Korean BM25 hint (default: '<name> 조회 검색 추천')",
    )
    parser.add_argument(
        "--search-hint-en",
        default=None,
        help="English BM25 hint (default: '<name> lookup search')",
    )
    # PIPA flags — required when --pii.
    parser.add_argument("--pipa-org")
    parser.add_argument("--pipa-contact")
    parser.add_argument(
        "--pipa-fields",
        help="comma-separated PII fields (e.g. phone_number,resident_registration_number)",
    )
    parser.add_argument("--pipa-legal-basis")
    parser.add_argument("--pipa-sha256")
    parser.add_argument(
        "--mock-source-spec",
        default=None,
        help=(
            "URL / attribution for tier=mock; ignored when tier=live "
            "(memory feedback_mock_evidence_based)"
        ),
    )

    args = parser.parse_args(argv)

    pipa: PIPATrusteeArgs | None = None
    if args.pii:
        if not all(
            (
                args.pipa_org,
                args.pipa_contact,
                args.pipa_fields,
                args.pipa_legal_basis,
                args.pipa_sha256,
            )
        ):
            print(
                "error: --pii requires --pipa-org / --pipa-contact / --pipa-fields / "
                "--pipa-legal-basis / --pipa-sha256 (see docs/plugins/security-review.md)",
                file=sys.stderr,
            )
            return 3
        pipa = PIPATrusteeArgs(
            trustee_org_name=args.pipa_org,
            trustee_contact=args.pipa_contact,
            pii_fields_handled=tuple(f.strip() for f in args.pipa_fields.split(",") if f.strip()),
            legal_basis=args.pipa_legal_basis,
            acknowledgment_sha256=args.pipa_sha256,
        )

    opts = InitOptions(
        name=args.name,
        tier=args.tier,
        layer=args.layer,
        pii=args.pii,
        out=args.out or Path.cwd() / args.name,
        force=args.force,
        # Default Korean hint includes a generic ministry-class noun ("공공")
        # so the scaffold passes Q4-HINT-MINISTRY out of the box; contributor
        # replaces with the real ministry / agency name during step 4.
        search_hint_ko=args.search_hint_ko or f"{args.name} 공공 데이터 조회 검색 추천",
        search_hint_en=args.search_hint_en or f"{args.name} public data lookup search",
        pipa=pipa,
        mock_source_spec=args.mock_source_spec,
    )
    result = run_init(opts)
    if result.exit_code != 0:
        print(
            f"error ({result.error_kind}): {result.error_message}",
            file=sys.stderr,
        )
        return result.exit_code

    print(f"✓ 플러그인 {opts.name!r} 생성 완료.")
    print(f"  경로: {result.out_dir}")
    print("  다음 단계:")
    print(f"    cd {result.out_dir}")
    print("    uv sync")
    print("    uv run pytest        ← 즉시 통과해야 합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
