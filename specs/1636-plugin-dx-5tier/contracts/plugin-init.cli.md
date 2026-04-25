# Contract — `kosmos plugin init <name>` CLI

**Surface**: `tui/src/commands/plugin-init.ts` (Ink + React, Spec 287 stack).
**Trigger**: User types `/plugin init <name>` in the TUI REPL OR runs `kosmos plugin init <name>` from a regular shell (entry-point binary delegates to the same TS module).
**Purpose**: Scaffold a new plugin in the current working directory with a passing `pytest` green out of the box (FR-002, FR-003).

## Arguments

| Position | Name | Required | Constraints | Description |
|---|---|---|---|---|
| 1 | `<name>` | ✓ | regex `^[a-z][a-z0-9_]*$`, max_length 64 | The plugin id; becomes both the directory name and `PluginManifest.plugin_id`. |

## Flags

| Flag | Default | Description |
|---|---|---|
| `--tier <live\|mock>` | (interactive prompt if omitted) | Force tier without prompt. |
| `--layer <1\|2\|3>` | (interactive prompt) | Force permission layer. |
| `--pii / --no-pii` | (interactive prompt) | Pre-set processes_pii. If `--pii`, the PIPA acknowledgment sub-flow is mandatory. |
| `--out <path>` | `./<name>/` | Output directory. Errors if exists and is non-empty unless `--force`. |
| `--force` | false | Overwrite an existing non-empty `--out` directory. |
| `--non-interactive` | false | Fail if any required value is missing instead of prompting. Used by CI / scripts. |

## Interactive prompts (Ink)

```
✻ KOSMOS Plugin Init
플러그인 이름 (plugin_id):  seoul-subway   ← from arg
 Tier (live/mock):           [Select]
 권한 레이어 (1/2/3):         [Select]
 PII 처리 여부 (yes/no):      [Select]
   ↳ if yes: PIPA 수탁자 정보:
              조직명          [TextInput]
              연락처          [TextInput]
              처리 PII 필드   [TextInput, comma-separated]
              법적 근거       [TextInput]
              acknowledgment 텍스트 (docs/plugins/security-review.md) 읽고 동의:  [yes/no]
                ↳ if yes: SHA-256 자동 계산 후 manifest 에 기록
 search_hint (한국어, 명사 3개 이상):  [TextInput]
 search_hint (English):              [TextInput]
```

## Emitted file tree

```
<out>/
├── pyproject.toml                          # uv-compatible, depends on kosmos-plugin-sdk (vendored stub)
├── manifest.yaml                           # PluginManifest.model_dump() encoded as YAML
├── plugin_<name>/
│   ├── __init__.py
│   ├── adapter.py                          # GovAPITool subclass + register() call
│   └── schema.py                           # input_schema + output_schema Pydantic v2 models
├── tests/
│   ├── __init__.py
│   ├── conftest.py                         # block_network fixture (Constitution §IV)
│   ├── test_adapter.py                     # happy-path + error-path tests; passes out of box
│   └── fixtures/
│       └── <tool_id>.json                  # synthetic fixture so tests pass without real API
├── .github/
│   └── workflows/
│       ├── plugin-validation.yml           # uses: umyunsang/KOSMOS/.github/workflows/plugin-validation.yml@<sha>
│       └── release-with-slsa.yml           # uses: slsa-framework/slsa-github-generator (R-3)
├── README.ko.md                            # Korean-primary scaffold (FR-010)
├── README.en.md                            # English secondary
└── .gitignore
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. Plugin scaffolded, `pytest` instructions printed. |
| 1 | Validation error (invalid name, missing required prompt in `--non-interactive`). |
| 2 | I/O error (cannot write to `<out>`). |
| 3 | PIPA acknowledgment text could not be read or hash mismatch (canonical text drift). |

## Success output

```
✓ 플러그인 'seoul-subway' 생성 완료.
  경로: ./seoul-subway/
  다음 단계:
    cd seoul-subway
    uv sync
    uv run pytest        ← 즉시 통과해야 합니다.
  문서:
    docs/plugins/quickstart.ko.md
    docs/plugins/architecture.md
```

## Telemetry

Emits OTEL span `kosmos.plugin.init` with attributes:
- `kosmos.plugin.id` = `<name>`
- `kosmos.plugin.tier` = `live` | `mock`
- `kosmos.plugin.layer` = `1` | `2` | `3`
- `kosmos.plugin.pii` = bool

No PII; safe to ship in default OTEL stream.

## Negative-path test cases (bun test, FR-002)

1. Invalid `<name>` (uppercase) → exit 1, error mentions `^[a-z][a-z0-9_]*$`.
2. Existing non-empty `<out>` without `--force` → exit 2, error mentions `--force`.
3. `--pii` without acknowledgment confirmation → exit 3, error points at `docs/plugins/security-review.md`.
4. Network permission test: scaffold's `tests/conftest.py` `block_network` fixture asserts no outbound socket — verified by attempting `httpx.get("https://example.com")` from `test_adapter.py` and expecting `RuntimeError`.

## Non-goals

- Not a build tool — does not run `pytest` automatically (the contributor does that).
- Not a publish tool — `kosmos plugin publish` is a separate command (deferred; not in P5).
- Not a marketplace browser — that's #1820 (deferred).
