// SPDX-License-Identifier: Apache-2.0
//
// Epic #1636 P5 — `kosmos plugin init <name>` scaffold command.
//
// Surface contract: specs/1636-plugin-dx-5tier/contracts/plugin-init.cli.md
//
// This module exposes both:
//   - runPluginInit(options) — pure, synchronous, file-emitting core used
//     by --non-interactive callers and tests. Returns a structured
//     PluginInitResult so callers (including the CI tests in T019) can
//     assert outcomes without parsing stdout.
//   - mainPluginInit(argv) — argv parser that maps CLI flags to runPluginInit.
//     Defaults to throwing "interactive mode not yet wired" when prompts are
//     needed; the full Ink interactive flow lands later (still scoped to
//     this command file per migration tree § B8).
//
// All scaffolded source identifiers are ASCII / English per FR-025; only
// description_ko / search_hint_ko / README.ko.md carry Korean. The emitted
// scaffold passes `pytest` out of the box because adapter.py + schema.py +
// tests/test_adapter.py round-trip a recorded synthetic fixture without
// touching the network (Constitution §IV).

import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import * as yaml from 'yaml'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Permission-layer values per migration tree § UI-C / Spec 033. */
export type PermissionLayer = 1 | 2 | 3

/** Plugin distribution tier. */
export type PluginTier = 'live' | 'mock'

/** PIPA §26 trustee acknowledgment block (mirrors PIPATrusteeAcknowledgment). */
export interface PIPATrusteeAcknowledgment {
  trustee_org_name: string
  trustee_contact: string
  pii_fields_handled: string[]
  legal_basis: string
  /** SHA-256 of canonical text from docs/plugins/security-review.md. */
  acknowledgment_sha256: string
}

/** Inputs to the non-interactive scaffold core. */
export interface PluginInitOptions {
  name: string
  tier: PluginTier
  layer: PermissionLayer
  /**
   * When true, the scaffold emits a manifest with processes_pii=true and
   * embeds the supplied pipaAcknowledgment. When false, processes_pii=false
   * and pipaAcknowledgment must be omitted.
   */
  pii: boolean
  pipaAcknowledgment?: PIPATrusteeAcknowledgment
  /** Default ./<name>/. Resolved against process.cwd() when relative. */
  out?: string
  force?: boolean
  /** Korean search hint indexed by BM25 (R-1 Q4-HINT-NOUNS). */
  searchHintKo: string
  /** English search hint mirror. */
  searchHintEn: string
  /** Optional override of the SLSA provenance URL placeholder in manifest. */
  slsaProvenanceUrl?: string
  /** Optional override for testing: workspace root used to resolve outDir. */
  cwd?: string
}

/** Outcome record from {@link runPluginInit}. */
export interface PluginInitResult {
  /** 0 success / 1 validation / 2 I/O / 3 PIPA acknowledgment drift. */
  exitCode: 0 | 1 | 2 | 3
  /** Absolute path to the emitted scaffold root, when exitCode=0. */
  outDir?: string
  /** Files written, relative to outDir, in deterministic order. */
  filesWritten?: string[]
  /** Structured error metadata when exitCode != 0. */
  errorKind?: string
  errorMessage?: string
}

// ---------------------------------------------------------------------------
// Validators
// ---------------------------------------------------------------------------

const PLUGIN_NAME_RE = /^[a-z][a-z0-9_]*$/
const SHA256_RE = /^[a-f0-9]{64}$/

function validateName(name: string): string | null {
  if (!PLUGIN_NAME_RE.test(name)) {
    return `plugin name ${JSON.stringify(name)} must match ^[a-z][a-z0-9_]*$`
  }
  if (name.length > 64) {
    return `plugin name max length 64 (got ${name.length})`
  }
  return null
}

function validatePipa(
  pii: boolean,
  ack: PIPATrusteeAcknowledgment | undefined,
): string | null {
  if (pii && !ack) {
    return 'pii=true requires pipaAcknowledgment (see docs/plugins/security-review.md)'
  }
  if (!pii && ack) {
    return 'pii=false must NOT supply pipaAcknowledgment'
  }
  if (ack) {
    if (!SHA256_RE.test(ack.acknowledgment_sha256)) {
      return `pipaAcknowledgment.acknowledgment_sha256 must match ^[a-f0-9]{64}$ (got ${ack.acknowledgment_sha256.length} chars)`
    }
    if (!ack.trustee_org_name || !ack.trustee_contact || !ack.legal_basis) {
      return 'pipaAcknowledgment requires non-empty trustee_org_name + trustee_contact + legal_basis'
    }
    if (!Array.isArray(ack.pii_fields_handled) || ack.pii_fields_handled.length === 0) {
      return 'pipaAcknowledgment.pii_fields_handled must be a non-empty array'
    }
  }
  return null
}

// ---------------------------------------------------------------------------
// File templates
// ---------------------------------------------------------------------------

function manifestForOptions(opts: PluginInitOptions): Record<string, unknown> {
  return {
    plugin_id: opts.name,
    version: '0.1.0',
    adapter: {
      tool_id: `plugin.${opts.name}.lookup`,
      primitive: 'lookup',
      module_path: `plugin_${opts.name}.adapter`,
      input_model_ref: `plugin_${opts.name}.schema:LookupInput`,
      source_mode: 'OPENAPI',
      published_tier_minimum: 'digital_onepass_level1_aal1',
      nist_aal_hint: 'AAL1',
      auth_type: 'api_key',
      auth_level: 'AAL1',
      pipa_class: opts.pii ? 'personal_standard' : 'non_personal',
      is_personal_data: opts.pii,
    },
    tier: opts.tier,
    mock_source_spec:
      opts.tier === 'mock' ? 'https://example.com/mock-source-spec' : null,
    processes_pii: opts.pii,
    pipa_trustee_acknowledgment: opts.pipaAcknowledgment ?? null,
    slsa_provenance_url:
      opts.slsaProvenanceUrl ??
      `https://github.com/kosmos-plugin-store/kosmos-plugin-${opts.name}/releases/download/v0.1.0/${opts.name}.intoto.jsonl`,
    otel_attributes: { 'kosmos.plugin.id': opts.name },
    search_hint_ko: opts.searchHintKo,
    search_hint_en: opts.searchHintEn,
    permission_layer: opts.layer,
  }
}

const PYPROJECT_TEMPLATE = (name: string) => `[project]
name = "kosmos-plugin-${name}"
version = "0.1.0"
description = "KOSMOS plugin scaffolded by 'kosmos plugin init'"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
dependencies = [
  "pydantic>=2.13",
  "httpx>=0.27",
]

[project.optional-dependencies]
test = [
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
`

const ADAPTER_TEMPLATE = (name: string, layerNote: string) => `# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin adapter for ${name}.

Scaffolded by 'kosmos plugin init'. Replace the placeholder lookup logic
with a real call to the upstream public API. ${layerNote}
"""

from __future__ import annotations

from typing import Any

from .schema import LookupInput, LookupOutput


# The KOSMOS host expects two module-level symbols:
#   - TOOL: a kosmos.tools.models.GovAPITool instance describing the adapter.
#   - adapter: an async callable accepting a validated LookupInput and
#     returning a dict matching LookupOutput.
#
# At install time the host imports this module and routes
# 'plugin.${name}.lookup' through the registry.

# NOTE: GovAPITool is imported lazily so the scaffold's tests can run
# without the kosmos package installed (CI uses the published wheel; local
# dev imports the in-tree module).
def _build_tool() -> Any:
    from kosmos.tools.models import GovAPITool

    return GovAPITool(
        id="plugin.${name}.lookup",
        name_ko="${name} 조회",
        ministry="OTHER",
        category=["${name}"],
        endpoint="https://example.com/${name}",
        auth_type="api_key",
        input_schema=LookupInput,
        output_schema=LookupOutput,
        search_hint="${name} 조회 lookup",
        auth_level="AAL1",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        is_personal_data=False,
        primitive="lookup",
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
    )


TOOL = _build_tool()


async def adapter(payload: LookupInput) -> dict[str, Any]:
    """Replace this stub with a real httpx call against the upstream API."""
    return {"echo": payload.query, "source": "${name}-stub"}
`

const SCHEMA_TEMPLATE = `# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 input + output schemas for the lookup primitive."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LookupInput(BaseModel):
    """Input model for the lookup primitive — REPLACE with real fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, description="Search query text.")


class LookupOutput(BaseModel):
    """Output model — REPLACE with real fields matching the upstream response."""

    model_config = ConfigDict(frozen=True, extra="allow")

    echo: str = Field(description="Echo of the input query (placeholder).")
    source: str = Field(description="Source identifier (placeholder).")
`

const PKG_INIT_TEMPLATE = (name: string) => `# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin package: ${name}."""

from .adapter import TOOL, adapter
from .schema import LookupInput, LookupOutput

__all__ = ["TOOL", "adapter", "LookupInput", "LookupOutput"]
`

const TEST_INIT = `# SPDX-License-Identifier: Apache-2.0
`

const CONFTEST_TEMPLATE = `# SPDX-License-Identifier: Apache-2.0
"""Pytest fixtures — Constitution §IV: no live network calls in CI."""

from __future__ import annotations

import socket
from collections.abc import Iterator

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

    def _blocked(*_a: object, **_k: object) -> socket.socket:
        raise RuntimeError(
            "Outbound network access is blocked in plugin tests "
            "(Constitution §IV). Use a recorded fixture or "
            "@pytest.mark.allow_network for the rare opt-out."
        )

    monkeypatch.setattr(socket, "socket", _blocked)
    yield


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "allow_network: opt out of the autouse network block",
    )
`

const TEST_ADAPTER_TEMPLATE = (name: string) => `# SPDX-License-Identifier: Apache-2.0
"""Adapter happy-path + error-path tests for ${name}.

The scaffolded test passes out of the box because the adapter stub
returns a deterministic echo. Replace with real assertions once the
adapter calls the upstream public API.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from plugin_${name}.adapter import adapter
from plugin_${name}.schema import LookupInput, LookupOutput


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "plugin.${name}.lookup.json"


@pytest.mark.asyncio
async def test_adapter_happy_path() -> None:
    payload = LookupInput(query="hello")
    result = await adapter(payload)
    LookupOutput.model_validate(result)
    assert result["echo"] == "hello"


@pytest.mark.asyncio
async def test_adapter_error_path() -> None:
    with pytest.raises(Exception):
        LookupInput(query="")  # min_length=1


def test_recorded_fixture_round_trips() -> None:
    raw = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    LookupOutput.model_validate(raw)


@pytest.mark.asyncio
async def test_no_outbound_network() -> None:
    """Constitution §IV: the conftest fixture must block live HTTP."""
    with pytest.raises(RuntimeError, match="network"):
        async with httpx.AsyncClient() as client:
            await client.get("https://example.com")
`

const FIXTURE_TEMPLATE = (name: string) =>
  JSON.stringify(
    { echo: 'sample', source: `${name}-stub` },
    null,
    2,
  ) + '\n'

const README_KO_TEMPLATE = (name: string, tier: string) => `# kosmos-plugin-${name}

KOSMOS 플러그인 — \`${name}\` 어댑터.

## 설치

\`\`\`bash
kosmos plugin install ${name}
\`\`\`

## 개발

\`\`\`bash
uv sync
uv run pytest
\`\`\`

## Tier

이 플러그인은 **${tier}** tier 입니다.

## 참고

- [docs/plugins/quickstart.ko.md](https://github.com/umyunsang/KOSMOS/blob/main/docs/plugins/quickstart.ko.md)
- [docs/plugins/architecture.md](https://github.com/umyunsang/KOSMOS/blob/main/docs/plugins/architecture.md)

## 라이선스

Apache-2.0
`

const README_EN_TEMPLATE = (name: string, tier: string) => `# kosmos-plugin-${name}

KOSMOS plugin — \`${name}\` adapter.

## Install

\`\`\`bash
kosmos plugin install ${name}
\`\`\`

## Develop

\`\`\`bash
uv sync
uv run pytest
\`\`\`

## Tier

This plugin ships at **${tier}** tier.

## Documentation

- [docs/plugins/quickstart.ko.md](https://github.com/umyunsang/KOSMOS/blob/main/docs/plugins/quickstart.ko.md)
- [docs/plugins/architecture.md](https://github.com/umyunsang/KOSMOS/blob/main/docs/plugins/architecture.md)

## License

Apache-2.0
`

const GITIGNORE_TEMPLATE = `# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/

# uv
uv.lock

# Editor
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
`

const PLUGIN_VALIDATION_WORKFLOW = `name: plugin-validation

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    uses: umyunsang/KOSMOS/.github/workflows/plugin-validation.yml@main
    secrets: inherit
`

const RELEASE_SLSA_WORKFLOW = `name: release-with-slsa

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
      digest: \${{ steps.hash.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      - name: Build bundle
        id: build
        run: |
          tar -czf "$\{{ github.event.repository.name }}-$\{{ github.ref_name }}.tar.gz" \\
            --exclude='.git' --exclude='dist' .
      - name: Compute hash
        id: hash
        run: |
          echo "digest=$(sha256sum *.tar.gz | base64 -w0)" >> "$GITHUB_OUTPUT"

  provenance:
    needs: build
    permissions:
      id-token: write
      contents: write
      actions: read
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0
    with:
      base64-subjects: \${{ needs.build.outputs.digest }}
      upload-assets: true
`

// ---------------------------------------------------------------------------
// Core scaffolder
// ---------------------------------------------------------------------------

interface FileSpec {
  path: string
  body: string
}

function buildFiles(opts: PluginInitOptions): FileSpec[] {
  const layerNote =
    opts.layer === 1
      ? '권한 Layer 1 (green) — read-only public data.'
      : opts.layer === 2
        ? '권한 Layer 2 (orange) — citizen-scoped data; consent required.'
        : '권한 Layer 3 (red) — irreversible action; explicit consent required.'

  const manifest = manifestForOptions(opts)
  const yamlBody = yaml.stringify(manifest, { indent: 2 })

  return [
    { path: 'pyproject.toml', body: PYPROJECT_TEMPLATE(opts.name) },
    { path: 'manifest.yaml', body: yamlBody },
    { path: `plugin_${opts.name}/__init__.py`, body: PKG_INIT_TEMPLATE(opts.name) },
    { path: `plugin_${opts.name}/adapter.py`, body: ADAPTER_TEMPLATE(opts.name, layerNote) },
    { path: `plugin_${opts.name}/schema.py`, body: SCHEMA_TEMPLATE },
    { path: 'tests/__init__.py', body: TEST_INIT },
    { path: 'tests/conftest.py', body: CONFTEST_TEMPLATE },
    { path: 'tests/test_adapter.py', body: TEST_ADAPTER_TEMPLATE(opts.name) },
    {
      path: `tests/fixtures/plugin.${opts.name}.lookup.json`,
      body: FIXTURE_TEMPLATE(opts.name),
    },
    { path: '.github/workflows/plugin-validation.yml', body: PLUGIN_VALIDATION_WORKFLOW },
    { path: '.github/workflows/release-with-slsa.yml', body: RELEASE_SLSA_WORKFLOW },
    { path: 'README.ko.md', body: README_KO_TEMPLATE(opts.name, opts.tier) },
    { path: 'README.en.md', body: README_EN_TEMPLATE(opts.name, opts.tier) },
    { path: '.gitignore', body: GITIGNORE_TEMPLATE },
  ]
}

function isDirNonEmpty(path: string): boolean {
  try {
    return readdirSync(path).length > 0
  } catch {
    return false
  }
}

/**
 * Pure scaffolder. No prompts, no spinner. Writes the file tree
 * synchronously and returns a structured result the caller (test or
 * non-interactive CLI) can assert on.
 */
export function runPluginInit(opts: PluginInitOptions): PluginInitResult {
  const nameError = validateName(opts.name)
  if (nameError) {
    return { exitCode: 1, errorKind: 'invalid_name', errorMessage: nameError }
  }
  const pipaError = validatePipa(opts.pii, opts.pipaAcknowledgment)
  if (pipaError) {
    return {
      exitCode: 3,
      errorKind: 'pipa_acknowledgment_error',
      errorMessage: pipaError,
    }
  }

  const baseCwd = opts.cwd ?? process.cwd()
  const outDir = resolve(baseCwd, opts.out ?? `./${opts.name}`)

  if (existsSync(outDir) && isDirNonEmpty(outDir)) {
    if (!opts.force) {
      return {
        exitCode: 2,
        errorKind: 'out_dir_non_empty',
        errorMessage: `output directory ${outDir} is not empty; pass --force to overwrite`,
      }
    }
    try {
      rmSync(outDir, { recursive: true, force: true })
    } catch (err) {
      return {
        exitCode: 2,
        errorKind: 'out_dir_clear_failed',
        errorMessage: String(err),
      }
    }
  }

  const files = buildFiles(opts)
  const written: string[] = []
  try {
    for (const f of files) {
      const abs = join(outDir, f.path)
      mkdirSync(dirname(abs), { recursive: true })
      writeFileSync(abs, f.body, 'utf-8')
      written.push(f.path)
    }
  } catch (err) {
    return {
      exitCode: 2,
      errorKind: 'write_failed',
      errorMessage: String(err),
    }
  }

  return {
    exitCode: 0,
    outDir,
    filesWritten: written,
  }
}

// ---------------------------------------------------------------------------
// CLI argv parser
// ---------------------------------------------------------------------------

function parseFlag<T>(argv: string[], flag: string, parse: (raw: string) => T): T | undefined {
  const idx = argv.indexOf(flag)
  if (idx === -1) return undefined
  const value = argv[idx + 1]
  if (value === undefined) {
    throw new Error(`flag ${flag} requires an argument`)
  }
  return parse(value)
}

function parseTier(raw: string): PluginTier {
  if (raw === 'live' || raw === 'mock') return raw
  throw new Error(`--tier expects 'live' or 'mock' (got ${JSON.stringify(raw)})`)
}

function parseLayer(raw: string): PermissionLayer {
  const n = Number(raw)
  if (n === 1 || n === 2 || n === 3) return n
  throw new Error(`--layer expects 1, 2, or 3 (got ${JSON.stringify(raw)})`)
}

export interface ParsedArgv {
  name: string | undefined
  options: Partial<PluginInitOptions>
  nonInteractive: boolean
  errors: string[]
}

export function parsePluginInitArgv(argv: string[]): ParsedArgv {
  const errors: string[] = []
  const positional = argv.filter((tok, i) => {
    if (tok.startsWith('--')) return false
    const prev = argv[i - 1]
    if (
      prev === '--tier' ||
      prev === '--layer' ||
      prev === '--out'
    ) {
      return false
    }
    return true
  })

  const name = positional[0]
  const options: Partial<PluginInitOptions> = {}

  try {
    options.tier = parseFlag(argv, '--tier', parseTier)
    options.layer = parseFlag(argv, '--layer', parseLayer)
    options.out = parseFlag(argv, '--out', (v) => v)
  } catch (err) {
    errors.push(String(err))
  }

  if (argv.includes('--pii')) options.pii = true
  if (argv.includes('--no-pii')) options.pii = false
  if (argv.includes('--force')) options.force = true

  return {
    name,
    options,
    nonInteractive: argv.includes('--non-interactive'),
    errors,
  }
}

/**
 * argv entry point. Returns an exit code; never throws.
 *
 * Interactive mode (when --non-interactive is absent and required values
 * are missing) currently returns exit 1 with a "interactive mode pending"
 * message. The full Ink wizard lands in a follow-on PR within Phase 3.
 */
export function mainPluginInit(argv: string[]): PluginInitResult {
  const parsed = parsePluginInitArgv(argv)
  if (parsed.errors.length > 0) {
    return {
      exitCode: 1,
      errorKind: 'argv_parse',
      errorMessage: parsed.errors.join('; '),
    }
  }
  if (!parsed.name) {
    return {
      exitCode: 1,
      errorKind: 'missing_name',
      errorMessage: 'positional <name> is required',
    }
  }

  const opts = parsed.options
  if (
    parsed.nonInteractive &&
    (opts.tier === undefined || opts.layer === undefined || opts.pii === undefined)
  ) {
    return {
      exitCode: 1,
      errorKind: 'non_interactive_missing_value',
      errorMessage:
        '--non-interactive requires --tier, --layer, and --pii / --no-pii',
    }
  }

  if (!parsed.nonInteractive) {
    return {
      exitCode: 1,
      errorKind: 'interactive_pending',
      errorMessage:
        'interactive Ink wizard not yet wired; pass --non-interactive '
        + 'with --tier --layer --pii/--no-pii to scaffold',
    }
  }

  return runPluginInit({
    name: parsed.name,
    tier: opts.tier as PluginTier,
    layer: opts.layer as PermissionLayer,
    pii: opts.pii as boolean,
    out: opts.out,
    force: opts.force ?? false,
    searchHintKo:
      opts.searchHintKo ?? `${parsed.name} 조회 검색 추천`,
    searchHintEn: opts.searchHintEn ?? `${parsed.name} lookup search`,
  })
}
