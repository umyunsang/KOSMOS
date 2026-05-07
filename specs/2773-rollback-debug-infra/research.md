# PR #2773 Rollback + Real-Use Debug Infra Research

Date: 2026-05-06

## Reference Bootstrap

- KOSMOS thesis: `docs/vision.md` defines KOSMOS as a Claude Code harness migration; tool loop, permission gauntlet, context assembly, and TUI remain the reference substrate.
- Canonical requirements: `docs/requirements/kosmos-migration-tree.md` requires the CC agent loop to be preserved and exposes only the five national-infrastructure primitives.
- CC restored source:
  - `.references/claude-code-sourcemap/restored-src/src/query.ts` keeps recoverable tool failures in the conversation as `tool_result` blocks with `is_error: true`.
  - `.references/claude-code-sourcemap/restored-src/src/components/messages/UserToolResultMessage/UserToolResultMessage.tsx` routes `param.is_error` to `UserToolErrorMessage`.
  - `.references/claude-code-sourcemap/restored-src/src/components/FallbackToolUseErrorMessage.tsx` renders fallback tool failures as error-colored text with a transcript expansion hint.
- Adapter docs:
  - `docs/api/nmc/emergency_search.md` models NMC coordinate and regional list operations explicitly; station/neighborhood ER scenarios require `resolve_location(want='all')` before region-mode NMC lookup.
  - `docs/api/kma/forecast_fetch.md` requires WGS-84 `lat` and `lon`, again obtained via `resolve_location`.
  - `docs/api/resolve_location/index.md` is the location meta-tool contract.
  - `specs/026-safety-rails/spec.md` requires tool-output ingress redaction before normalization, while preserving clean public-API outputs below the detector false-positive ceiling.
  - `specs/2773-rollback-debug-infra/nmc-curl-evidence.md` records direct curl evidence for Kakao region resolution and NMC Hadan/Saha-gu responses.
  - `specs/2773-rollback-debug-infra/location-koroad-curl-evidence.md` records direct curl evidence for Kakao POI → coord2regioncode and KOROAD `numOfRows/pageNo`.
  - `specs/2773-rollback-debug-infra/nfa-curl-evidence.md` records direct curl evidence for the NFA 119 statistical lookup contract.
  - `specs/2773-rollback-debug-infra/mohw-curl-evidence.md` records direct curl evidence for SSIS one-parent welfare parameters.

## External Primary Sources

- Bun `spawn` supports real PTY execution through the `terminal` option for interactive terminal apps: <https://bun.com/docs/runtime/child-process>
- vhs supports output recording plus `Screenshot` PNG capture: <https://github.com/charmbracelet/vhs>
- Ink testing library exposes both `lastFrame()` and the full `frames` array; KOSMOS audits must inspect the sequence, not only the last frame: <https://github.com/vadimdemedes/ink-testing-library>
- tmux `capture-pane -p` writes pane content to stdout, which is suitable for text snapshots: <https://man7.org/linux/man-pages/man1/tmux.1.html>
- pyte is an in-memory VTxxx-compatible terminal emulator for replay/screen-scrape workflows: <https://pyte.readthedocs.io/en/latest/>
- MCP tool results may contain structured and unstructured content; KOSMOS should keep adapter envelopes structured and visible to the UI layer: <https://modelcontextprotocol.io/specification/draft/server/tools>
- OpenTelemetry GenAI conventions include spans/events/exceptions for GenAI systems and tool flows: <https://opentelemetry.io/docs/specs/semconv/gen-ai/>
- OpenAI trace grading recommends grading agent traces for workflow-level issues such as tool choice, handoff, instruction violations, and routing regressions: <https://developers.openai.com/api/docs/guides/agent-evals>

## Decisions

1. Roll back PR #2773 as a single revert commit rather than trying to salvage its 4,996-file mixed change set. The merged scope mixed source changes, prompts, docs, generated captures, and workflow-adjacent artifacts; fixing it in place would make the reference-first boundary unauditable.
2. Keep the pre-#2773 chain guard pattern: a missing `lat/lon` failure for KMA/NMC must stay inside the agentic loop and force `resolve_location` before retrying the lookup. The user-visible failure was a terminal loop break, not merely a bad error string.
3. Treat nested primitive result errors as CC tool errors. A KOSMOS envelope such as `{kind:"lookup", result:{kind:"error"}}` is semantically equivalent to CC's `is_error` tool result and must render through `UserToolErrorMessage`.
4. Add real-use trace grading as a repo-local script. The audit checks chronological frames, recoverable-error retry, CC error rendering, expanded trace visibility, and raw protocol leakage.
5. Make frame sampling default-on in both PTY harnesses. Capturing only `final.txt` reproduces the exact blind spot that allowed the regression through.
6. Split `nmc_emergency_search` into explicit `mode="coordinate"` and `mode="region"` contracts. Curl evidence proved the coordinate operation accepts valid Hadan parameters but returns 0 rows, while the official regional list operation returns `큐병원` for `Q0=부산광역시`, `Q1=사하구`. This is not implemented as fallback; the LLM must choose the official operation through schema and description.
7. Enrich `resolve_location` coordinate outputs with official KMA `nx/ny` grid coordinates and add a coordinate-derived Kakao `coord2regioncode` leg for administrative codes. This prevents the model from filling missing KMA/KOROAD parameters from memory after a successful POI/station coordinate lookup.
8. Expose KOROAD hazard pagination fields because direct curl proved `numOfRows/pageNo` are accepted official wire parameters. The earlier validation error was an adapter schema gap, not an upstream rejection.
9. Tighten the `phone_kr` PII pattern boundary instead of adding a field allowlist or disabling safety redaction. Real-use KOROAD frames showed `lo_crd="127.019851372856"` rendered as `127.<PHONE_KR>6`; the root cause was the phone regex matching a substring inside a decimal coordinate. Coordinates are clean public-API output, so this belongs at the PII-pattern false-positive boundary while standalone Korean mobile numbers continue to redact.
10. Split the NFA scenario by real adapter contract. `nfa_emergency_info_service` is a monthly anonymized EMS-statistics API; gas-leak safety instructions are not that API. The real-use matrix now tests NFA with a direct-curl-proven statistical query and separately forbids misrouting a gas-safety question into the NFA statistics adapter.
11. Add the official SSIS target-household code reference to the MOHW adapter metadata. Direct curl proved `trgterIndvdlArray=060` is the valid one-parent/grandparent household filter; both `searchWrd=한부모가족 아동양육비 지원` and `searchWrd=아동양육비` return `WLF00001068` with `resultCode=0`. The model's failed real-use path treated 한부모 as a life-stage problem, so the fix is to expose the agency code boundary, not to add fallback routing.
12. Tighten the `passport_kr` PII pattern boundary instead of field-allowlisting MOHW IDs. Real-use welfare frames showed `WLF00001068` rendered as `WL<PASSPORT_KR>` because the old passport regex matched the `F00001068` substring inside a public service identifier. A surrounding alphanumeric boundary preserves standalone Korean passport redaction while leaving official welfare IDs readable.
13. Remove KOSMOS-only Y/A/N permission hotkeys from the primitive permission surface. The CC reference `PermissionPrompt` presents a `Select` list driven by Up/Down + Enter, and only uses the optional option-level `keybinding` field when a caller explicitly opts in. KOSMOS should preserve that selector behavior and use CC's Tab amend flow for optional text instead of adding a separate visible hotkey contract.

## Rejected

- Keyword routing fixes in prompts only. They do not prove the tool loop recovered after an adapter error.
- Automatic "coordinate 0건 → region retry" inside the adapter. That would hide the official operation boundary and recreate an unauditable fallback.
- Live data.go.kr or government API calls in CI. Adapter shape can be tested with fixtures and captures; live credentials remain local-only.
- Final-frame-only smoke. This misses transient flashes, premature final answers, raw IPC leaks, and missing expand traces.
- Hardcoded administrative-code repair. `강남역` must resolve through Kakao keyword coordinates and `coord2regioncode`, not a static or remembered `1168010100`.
- Field-name allowlists for coordinate redaction. The observed failure is a pattern-boundary false positive; a field allowlist would hide the same defect in any future decimal-valued public output.
- Forcing NFA statistics on general gas-safety advice. That would make the tool look active while returning the wrong agency contract for the citizen's intent.
- Treating an ambiguous welfare-application prompt as immediately submittable. `mock_welfare_application_submit_v1` requires an applicant identifier and household size; the real-use application scenario must provide those user-supplied fields or expect a clarifying question before submit.
