# Implementation Plan: KFTC OpenGiro Send Adapter

**Branch**: `2799-kftc-opengiro-send` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `specs/2799-kftc-opengiro-send/spec.md`  
**Epic**: [#2951](https://github.com/umyunsang/UMMAYA/issues/2951) under Initiative [#2290](https://github.com/umyunsang/UMMAYA/issues/2290)

## Summary

Add a KFTC OpenGiro `send` adapter family as a credential-blocked mock-to-live surface: official KFTC OpenGiro public pages define bill and payment endpoints, but the logged-in developer portal currently blocks API Key registration until a Callback URL is registered and keeps OpenGiro documents access-denied. Per UMMAYA's adapter rule, this feature therefore ships fixture-backed, source-cited `send` adapters and operator setup/evidence artifacts now, while keeping live OpenGiro execution fail-closed until KFTC callback/API-key readiness and sanitized direct-curl evidence exist.

The implementation reuses UMMAYA's existing `send` sub-registry, deterministic `SubmitOutput` envelope, discovery bridge, schema builder, and mock transparency stamping. It does not add a new primitive or live financial gateway route in this epic.

## Technical Context

**Language/Version**: Python 3.12+ (existing backend baseline; no version bump)  
**Primary Dependencies**: Existing `pydantic` v2, `pydantic-settings`, `httpx`, `pytest`, `pytest-asyncio`, stdlib `logging`; no new runtime dependencies  
**Storage**: No persistent storage changes. Operator secrets remain in UMMAYA-prefixed environment variables or operator secret storage outside the repo. Fixture artifacts live under repository test/docs paths and contain no live KFTC secrets.  
**Testing**: `uv run pytest` focused tests; schema check via `uv run python scripts/build_schemas.py --check`; no live KFTC calls in default tests or CI  
**Target Platform**: macOS/Linux developer workstations and GitHub Actions Ubuntu CI for fixture-only verification  
**Project Type**: Single Python package plus docs/tests  
**Performance Goals**: Adapter fixture invocation remains sub-10 ms excluding test harness overhead; schema generation remains deterministic; no external network call in default test path  
**Constraints**: Secret-safe, fail-closed, no `Any` in new I/O schemas, stdlib `logging` only, English source text except Korean domain data, no CI live calls, no arbitrary Callback URL portal registration by the agent  
**Scale/Scope**: Two `send` adapters for OpenGiro modules: bill service and payment service. One operator setup/readiness guide. One official-source evidence matrix. JSON Schema exports and docs catalog updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evaluation |
|---|---|---|
| **I. Reference-Driven Development** | PASS | Research maps decisions to `docs/vision.md`, `docs/requirements/ummaya-migration-tree.md`, restored Claude Code OAuth callback/deps patterns, existing UMMAYA `send` implementation, and official KFTC developer pages. |
| **II. Fail-Closed Security** | PASS | KFTC live credentials are not read from the browser or committed. Adapter policy cites KFTC official pages. Missing Callback/API-key readiness returns setup blockers. |
| **III. Pydantic v2 Strict Typing** | PASS | New adapter input models use frozen Pydantic v2 models with explicit fields. Outputs reuse `SubmitOutput`. No `Any` in new I/O schemas. |
| **IV. Government API Compliance** | PASS | No live KFTC calls in CI. Live probing remains marked and blocked until operator readiness evidence exists. Rate limits and credentials are explicit. |
| **V. Policy Alignment** | PASS | Supports Korea AX public-service integration through a single UMMAYA conversational surface while preserving consent and explainability. |
| **VI. Deferred Work Accountability** | PASS | Spec deferred table contains three tracked follow-up issues created by `/speckit-taskstoissues`: #2979, #2980, and #2981. No untracked deferral prose remains. |

**Gate verdict**: PASS pre-research and PASS post-design.

## Project Structure

### Documentation (this feature)

```text
specs/2799-kftc-opengiro-send/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── opengiro-send-contract.md
│   ├── operator-setup-contract.md
│   └── live-probe-evidence-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/ummaya/
├── settings.py                         # add UMMAYA_KFTC_* non-secret and secret settings
├── tools/
│   ├── models.py                       # add KFTC ministry enum
│   ├── mock/__init__.py                # import KFTC OpenGiro fixture-backed send adapters
│   └── mock/kftc/
│       ├── __init__.py
│       └── opengiro.py                 # bill + payment send adapters, fixture-first
└── primitives/submit.py                # no shape change; reused by adapters

docs/api/
├── README.md                           # add KFTC OpenGiro rows under send
├── submit/kftc_opengiro.md             # seven-section adapter doc
└── schemas/
    ├── mock_kftc_opengiro_bill_send_v1.json
    └── mock_kftc_opengiro_payment_send_v1.json

tests/
├── unit/tools/test_mock_kftc_opengiro.py
├── integration/test_kftc_opengiro_discovery.py
└── lint/test_kftc_secret_redaction.py
```

**Structure Decision**: Keep the work in the existing mock/send adapter architecture because KFTC credentials are not live-ready. The adapter IDs use the `mock_` prefix until sanitized live evidence exists; the public KFTC endpoint URLs are still recorded as the official target surface for mock-to-live migration.

## Complexity Tracking

No constitution violations. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0: Outline & Research - completed

See [research.md](./research.md). Key decisions:

1. OpenGiro maps to `send`, not `find`, because bill/payment operations are financial side effects.
2. The implementation must be fixture-backed and `mock_`-prefixed now because Callback URL and API Key registration are not complete.
3. Two adapters are cleaner than one operation-switching adapter: OpenGiro bill service and OpenGiro payment service are separate KFTC modules with different endpoint groups.
4. No arbitrary portal Callback URL will be registered in this epic. Operator setup documents the canonical callback expectation and leaves portal registration to the deployment owner.
5. Live `send` gateway generalization remains deferred because current live gateway code only allows `find`/`locate`.

## Phase 1: Design & Contracts - completed

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md). Summary:

- `OpenGiroBillParams` covers bill creation, bill cancellation, and payment-status inquiry fixture shapes.
- `OpenGiroPaymentParams` covers payment URL creation and payment result inquiry fixture shapes.
- `OpenGiroSetupReadiness` documents service, callback, key registration, document access, and tool access state.
- Contracts define the send adapter behavior, operator setup flow, and required live-probe evidence before any future live enablement.
