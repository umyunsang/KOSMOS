# Tasks: KFTC OpenGiro Send Adapter

**Input**: Design documents from `/specs/2799-kftc-opengiro-send/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by FR-007. Test tasks are listed before their corresponding implementation tasks and must avoid live KFTC calls.

**Organization**: Tasks are grouped by user story so each increment is independently testable.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the feature branch is ready and preserve the implementation dispatch record.

- [X] T001 Verify repository ignore rules already cover `.env`, `secrets/`, Python caches, and generated test artifacts in `.gitignore`
- [X] T002 Create implementation dispatch tree for this feature in `specs/2799-kftc-opengiro-send/dispatch-tree.md`
- [X] T003 [P] Add fixture evidence directory placeholders in `specs/2799-kftc-opengiro-send/evidence/README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared metadata and configuration required before the OpenGiro stories can register adapters safely.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Add KFTC ministry metadata support in `src/ummaya/tools/models.py`
- [X] T005 Add UMMAYA-prefixed KFTC OpenGiro readiness settings in `src/ummaya/settings.py`
- [X] T006 [P] Create KFTC mock package module scaffolding in `src/ummaya/tools/mock/kftc/__init__.py`
- [X] T007 Register the KFTC mock package side effect import in `src/ummaya/tools/mock/__init__.py`

**Checkpoint**: Shared metadata and import paths exist; user story implementation can proceed.

---

## Phase 3: User Story 1 - Classify OpenGiro as a Send Channel (Priority: P1) MVP

**Goal**: Maintainers can verify that KFTC OpenGiro belongs under the `send` primitive with official-source citations.

**Independent Test**: Review generated docs/catalog rows and confirm OpenGiro is not classified as read-only lookup.

### Tests for User Story 1

- [X] T008 [P] [US1] Add discovery/catalog integration tests for OpenGiro `send` classification in `tests/integration/test_kftc_opengiro_discovery.py`

### Implementation for User Story 1

- [X] T009 [US1] Add official-source OpenGiro adapter documentation in `docs/api/submit/kftc_opengiro.md`
- [X] T010 [US1] Update adapter catalog references for OpenGiro `send` rows in `docs/api/README.md`

**Checkpoint**: OpenGiro classification is independently reviewable from docs and discovery tests.

---

## Phase 4: User Story 2 - Register a Safe KFTC Credential Path (Priority: P1)

**Goal**: Operators can understand and validate KFTC readiness without exposing Client Secret values.

**Independent Test**: Run the setup/readiness and redaction tests; no secret values or live calls are required.

### Tests for User Story 2

- [X] T011 [P] [US2] Add KFTC setup readiness tests in `tests/unit/tools/test_mock_kftc_opengiro.py`
- [X] T012 [P] [US2] Add KFTC secret-redaction lint tests in `tests/lint/test_kftc_secret_redaction.py`

### Implementation for User Story 2

- [X] T013 [US2] Implement OpenGiro setup readiness models and fail-closed helper logic in `src/ummaya/tools/mock/kftc/opengiro.py`
- [X] T014 [US2] Document KFTC Callback URL and API Key readiness workflow in `docs/api/submit/kftc_opengiro.md`

**Checkpoint**: Missing callback/API-key/secret readiness is represented as a setup blocker and secrets are not exposed.

---

## Phase 5: User Story 3 - Invoke OpenGiro Through the Send Envelope (Priority: P2)

**Goal**: UMMAYA sessions can invoke fixture-backed OpenGiro bill and payment actions through the existing `send` envelope.

**Independent Test**: Run unit tests that call `send(SubmitInput(...))` for valid, invalid, rejected, expired, and missing-credential fixture paths.

### Tests for User Story 3

- [X] T015 [P] [US3] Add bill adapter happy/error path tests in `tests/unit/tools/test_mock_kftc_opengiro.py`
- [X] T016 [P] [US3] Add payment adapter happy/error path tests in `tests/unit/tools/test_mock_kftc_opengiro.py`

### Implementation for User Story 3

- [X] T017 [US3] Implement `mock_kftc_opengiro_bill_send_v1` models and submit registration in `src/ummaya/tools/mock/kftc/opengiro.py`
- [X] T018 [US3] Implement `mock_kftc_opengiro_payment_send_v1` models and submit registration in `src/ummaya/tools/mock/kftc/opengiro.py`
- [X] T019 [US3] Add deterministic sanitized receipt mapping for success, pending, failed, and rejected OpenGiro outcomes in `src/ummaya/tools/mock/kftc/opengiro.py`

**Checkpoint**: Both OpenGiro adapters execute through `send` and return `SubmitOutput` without live KFTC calls.

---

## Phase 6: User Story 4 - Preserve Mock-to-Live Evidence (Priority: P3)

**Goal**: Future live conversion can trace every OpenGiro field to official KFTC evidence or a documented portal blocker.

**Independent Test**: Run schema generation/checks and inspect evidence artifacts for official URLs and blocked-live criteria.

### Tests for User Story 4

- [X] T020 [P] [US4] Add schema export assertions for OpenGiro send adapters in `tests/integration/test_kftc_opengiro_discovery.py`

### Implementation for User Story 4

- [X] T021 [US4] Generate OpenGiro submit JSON schema exports in `docs/api/schemas/mock_kftc_opengiro_bill_send_v1.json` and `docs/api/schemas/mock_kftc_opengiro_payment_send_v1.json`
- [X] T022 [US4] Backfill deferred tracking issue numbers in `specs/2799-kftc-opengiro-send/spec.md`
- [X] T023 [US4] Record sanitized official-source and portal-blocker evidence in `specs/2799-kftc-opengiro-send/evidence/README.md`

**Checkpoint**: Mock-to-live state is documented and schema exports match registered adapters.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full feature and prepare it for PR review.

- [X] T024 Run quickstart verification commands from `specs/2799-kftc-opengiro-send/quickstart.md`
- [X] T025 Run focused tests for KFTC OpenGiro adapters with `uv run pytest tests/unit/tools/test_mock_kftc_opengiro.py tests/integration/test_kftc_opengiro_discovery.py tests/lint/test_kftc_secret_redaction.py`
- [X] T026 Run full non-live test suite with `uv run pytest`
- [X] T027 Update task checkboxes in `specs/2799-kftc-opengiro-send/tasks.md` after verification completes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks user stories.
- **US1 and US2 (Phases 3-4)**: Can start after Foundational and are both P1.
- **US3 (Phase 5)**: Depends on US1 classification and US2 readiness helpers.
- **US4 (Phase 6)**: Depends on registered adapters and generated schema evidence.
- **Polish (Phase 7)**: Depends on all selected user stories being complete.

### User Story Dependencies

- **US1**: No dependency beyond Foundational.
- **US2**: No dependency beyond Foundational.
- **US3**: Depends on US1 and US2.
- **US4**: Depends on US3.

### Parallel Opportunities

- T003 can run in parallel with T001-T002.
- T006 can run in parallel with T004-T005 before T007 wires imports.
- T008, T011, and T012 can be authored in parallel because they touch separate test concerns.
- T015 and T016 can be authored in parallel in the same test file only if coordinated; otherwise keep sequential in a solo implementation.
- T020 can run after adapter IDs are stable and before schema generation.

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational tasks.
2. Complete US1 and US2 to establish primitive classification plus safe credential readiness.
3. Validate docs and readiness tests before writing send execution code.

### Incremental Delivery

1. Add OpenGiro classification and metadata.
2. Add fail-closed setup readiness.
3. Add bill and payment adapters through the shared `send` primitive.
4. Generate schemas and preserve mock-to-live evidence.

### Team Strategy

This feature has more than three logical tasks but tightly coupled adapter, schema, and test files. The current implementation will be Lead-solo to avoid unsupported Sonnet delegation in this Codex environment and to keep the credential-sensitive changes in one review context.

---

## Notes

- Total tasks: 27, below the 90-task Epic budget.
- No task may call live KFTC from CI.
- No task may reveal, print, or commit KFTC Client Secret, access token, authorization code, or raw personal financial identifiers.
- PR must close the Epic issue only; task sub-issues are linked for tracking and closed after merge.
