# Codex Goal: KOSAX Final Packaging Readiness

## Ultimate Goal

Make KOSAX packaging-ready as a client-side reference implementation for Korea's national AX infrastructure.

KOSAX is not a demo app and this goal is not "fix one module." The real product target is a conversational execution surface where a citizen asks for an outcome and KOSAX decomposes, routes, verifies, asks permission, calls the right Korean public-service tools, renders inspectable evidence, and either completes the action or gives a legally/technically honest handoff.

Canonical thesis:

- KOSAX = Claude Code original harness + two swaps.
- Swap 1: Anthropic model surface becomes FriendliAI Serverless + K-EXAONE.
- Swap 2: developer tools become Korean public-service / national-infrastructure tools.
- Everything else follows the Claude Code restored source unless a documented Korean public-service constraint requires an explicit adaptation.

The work is complete only when the harness abstraction holds across realistic citizen scenarios, not when an isolated adapter call succeeds.

## Source Of Truth Hierarchy

Use these sources in this order. If sources conflict, stop and document the conflict before implementing.

1. `AGENTS.md`
2. `docs/onboarding/codex-continuation.md`
3. `docs/vision.md`
4. `docs/requirements/kosax-migration-tree.md`
5. `.agents/skills/kosax-reference-first/SKILL.md`
6. `.references/claude-code-sourcemap/restored-src/`
7. Local adapter docs under `docs/api/`, `specs/`, and local downloaded agency docs
8. Official agency/API/standard/vendor documentation
9. Community open-source implementations only as secondary implementation insight, never as authority over official specs or CC parity

Never proceed from model memory when a primary source can be read.

## Research Material Discovery Skill Gate

Research material discovery is also a skill-driven workflow. Do not search for references ad hoc from memory or generic web habits.

Before collecting or using research material, explicitly invoke and follow:

- `$kosax-reference-first`
- Skill file: `.agents/skills/kosax-reference-first/SKILL.md`

This skill is mandatory for:

- Finding CC restored-source reference paths.
- Finding KOSAX canonical docs and active spec artifacts.
- Finding adapter/API docs under `docs/api/`, `specs/`, and local downloaded agency documents.
- Deciding when external primary-source research is required.
- Enforcing direct `curl` as first-class evidence for live public API endpoint/key/parameter validation.
- Producing the reference bootstrap note before implementation.

When the task concerns OpenAI/Codex/ChatGPT/OpenAI API behavior, also use the `openai-docs` skill and the `openaiDeveloperDocs` MCP server before any fallback search.

Every research pass must output a research-source ledger with:

- Skill used.
- Query or file-search pattern used.
- Source path or URL.
- Source authority level: CC source, KOSAX canonical doc, local adapter doc, official primary source, upstream open source, community secondary source.
- Decision supported by that source.
- Unknowns or blocked evidence.

## Hard Rules

- Use `kosax-reference-first` before planning or editing runtime behavior.
- Use `kosax-reference-first` before research-material discovery for KOSAX runtime, adapter, TUI, tool-loop, workflow, or verification decisions.
- Read CC restored source before changing tool loop, permission UX, TUI rendering, keybindings, context assembly, IPC, error handling, or debug infrastructure.
- Do not modify `.references/`.
- Do not add hardcoded routing, keyword gates, static service matrices, static policy tables, or fallback branches.
- Do not make synthetic fallback behavior to "make it work."
- Do not swallow errors with broad catches or convert operational failures into successful prose.
- Do not stub missing runtime behavior. Port the real module, fix the call site, or remove the dead call with evidence.
- Do not claim success unless the exact verification was run and passed.
- Live public API validation must start with direct `curl`; helper scripts can automate later but are not primary endpoint/key/parameter evidence.
- For live APIs, prove credential acceptance/rejection, endpoint URL, required fields, optional fields, encoded parameter values, response headers, result code, total count, and payload shape.
- If an official live API returns zero results, first prove the request is valid before proposing alternate paths.
- Never call live government, identity, payment, certificate, utility, or citizen-infrastructure channels from CI tests.
- Privileged actions must be evidence-graded mock unless KOSAX has official credential, legal authority, and documented permission policy.
- Permission classification must cite agency policy; KOSAX must not invent policy classes.
- Tool errors must remain visible, styled as errors, inspectable, and traceable.
- Source code text must be English except Korean domain data.
- Use stdlib `logging`; no `print()` outside CLI output layers.
- Use Pydantic v2 for tool I/O; do not use `Any`.
- Use env vars prefixed `KOSAX_`; never commit `.env`, `secrets/`, or local Codex config.
- Do not add dependencies outside a spec-driven PR.
- Do not introduce Go or Rust. TypeScript is allowed only in the TUI layer.
- Do not commit files over 1 MB without asking.
- Do not use destructive git commands, force-push, publish packages, merge PRs, or bypass signing unless the latest user instruction explicitly asks for that action.
- Preserve unrelated dirty worktree changes.

## Work Scope

Treat every observed bug as a possible abstraction failure in one of these layers:

- Query engine: agentic loop, retry/recovery, termination, context carryover, tool-result handling.
- Tool system: registry search, adapter metadata, Pydantic schemas, primitive envelopes, live/mock/handoff boundaries.
- Permission pipeline: CC-style permission request, Up/Down/Enter selection, Esc cancel, Tab feedback, policy citation, response propagation.
- TUI/UX: CC-style rendering, red error surfaces, transcript expand/collapse, frame stability, Korean text layout, painting/repaint anomalies.
- IPC/backend flow: NDJSON frame contract, correlation IDs, permission request/response, tool call/result visibility.
- Reasoning flow: model sees the right primitive signatures and adapter metadata, resolves missing information through available tools, and does not stop after recoverable validation errors.
- Context assembly: system prompt, session guidance, retrieval, memory, prompt cache stability.
- Observability/debugging: logs, frame captures, curl evidence, traceable scenario artifacts.
- Packaging readiness: tests, CI assumptions, docs, release notes, reproducible setup, local real-use readiness.

Do not narrow the goal to one adapter, one modal, or one scenario. Use those failures to repair the reusable harness boundary.

## Debugging Infrastructure Requirements

Absence of thrown errors is not evidence of correctness. A scenario fails if the user-facing flow, interaction flow, reasoning flow, tool-call flow, backend flow, rendering flow, painting flow, or debug-inspection flow is abnormal even when no exception is raised.

The debugging infrastructure must make these non-exception failures visible:

- UI/UX flow: the screen must explain what is happening at each step without misleading prose, stale status text, hidden permission state, or silent terminal completion.
- Interactive flow: keyboard input, Enter submission, Up/Down selection, Esc cancel, Tab feedback, transcript expansion, scrolling, and interruption must behave like a real human TUI session.
- Reasoning flow: the model must not stop after recoverable validation errors; it must use available tools, registry metadata, adapter schemas, and user clarification when appropriate.
- Tool-call flow: every tool call must expose selected tool id, normalized parameters, dispatch status, result status, raw/structured error, and follow-up decision.
- Backend flow: NDJSON frames, correlation IDs, permission request/response, tool call/result, and final assistant response must form one reconstructible transaction.
- Visualization flow: primitive renderers must show domain results, citations, receipts, warnings, and errors in the intended citizen-readable surface.
- Painting flow: intermediate frames must not flash wrong state, duplicate stale content, hide active modals, overlap text, or repaint into incoherent layout.
- Debug-inspection flow: expanded logs must let an inspector explain exactly why the model chose a tool, what parameters were sent, what the adapter returned, and why the next step happened.

Mandatory probe points for any suspected TUI/tool-loop defect:

- Input ingress: capture keypress/input event, timestamp, transaction id, and active mode.
- IPC frame boundary: capture `chat_request`, assistant chunks, `tool_call`, `tool_result`, `permission_request`, and `permission_response` with correlation ids.
- Tool dispatch boundary: capture tool id, primitive, normalized arguments, status, duration, error class, and adapter source.
- Render commit: capture every significant frame or frame hash, not only final output.
- Snapshot trigger: store PTY/frame artifacts under the active spec capture directory for every real-use scenario used as evidence.

Required artifact classes:

- Direct `curl` evidence for live API contract validation.
- Real-use TUI/PTY captures for human-like interaction flow.
- Full frame sequence or de-duplicated frame snapshots for UI and painting analysis.
- Expanded transcript or equivalent inspectable tool-detail capture.
- Scenario audit summary that records abnormal flows even when process exit code is zero.
- Root-cause note mapping each fix to a contract boundary and source reference.

Anti-patterns that invalidate a success claim:

- Checking only command exit code.
- Checking only the final frame.
- Grepping for one literal and treating no match as proof.
- Ignoring visible weirdness because tests passed.
- Treating model retry after an avoidable invalid-parameter call as success without investigating why the invalid call happened.
- Letting a permission modal render while backend continuation is stuck.
- Allowing a result to be correct while the user could not inspect how it was produced.

## LLMOps Rendering-Flow Verification

Use the LLMOps rendering verification infrastructure researched for KOSAX. Do not perform rendering checks as isolated screenshot review. Every real-use scenario must be evaluated as a correlated execution trace from model reasoning to final terminal pixels.

Use Langfuse/OTEL trace ids, `correlation_id`, `transaction_id`, and `frame_seq` as join keys across:

- User input event and input-mode state.
- `chat_request` frame carrying conversation history and tool definitions.
- LLM streaming chunks, including `kosax.llm.chunk` timing when available.
- Tool selection, normalized tool arguments, adapter dispatch, adapter result, and adapter error.
- `permission_request` and `permission_response` frames.
- `kosax.tui.frame_commit` render events and frame hashes when available.
- Bun PTY / tmux / vhs / frame snapshot artifacts.
- Expanded transcript/tool-detail capture visible to the user.
- Scenario audit result and root-cause note.

For each scenario, build or update an LLMOps timeline that answers these questions:

- Did the model choose the correct primitive and adapter from metadata rather than static routing?
- Did every missing parameter become either a tool-mediated recovery step or a structured citizen-input request?
- Did the backend emit the expected IPC frames in the same transaction?
- Did the TUI render each state in the same order as the backend/LLM/tool timeline?
- Did permission UI appear only when the backend requested permission, and did the decision propagate back to the same transaction?
- Did a tool error render as an error at the moment it happened, not later as ordinary prose?
- Did expanded detail expose the exact tool parameters and adapter response that the LLMOps trace shows?
- Did any intermediate frame flash stale, misleading, overlapping, or logically impossible state?

Required LLMOps artifacts for rendering-flow claims:

- `scripts/tui-realuse-matrix.py` scenario output.
- `scripts/tui-realuse-audit.py` audit output, extended or manually annotated when a non-exception flow is abnormal.
- Bun-native PTY capture for keystroke-sensitive scenarios, especially Esc, Tab, arrows, Ctrl keys, and permission prompts.
- vhs `.gif`, `.txt`, `.ascii`, and PNG keyframes where the active TUI verification spec requires visual review.
- Full de-duplicated frame directory or frame sequence hash, using `waitForFrame` / `frameStreamSnapshot` helpers for Ink-level checks when applicable.
- Timeline file that joins LLM chunk, IPC frame, tool dispatch, permission, and render commit events by trace/correlation ids.
- Written verdict for UI/UX, interaction, backend, reasoning, tool-call, visualization, painting, and debug-inspection flow.

The LLMOps verdict must fail the scenario even if process exit code is zero when the timeline proves any abnormal flow. A green unit test, green typecheck, or correct final answer does not override a failed LLMOps rendering-flow verdict.

## Required Abstractions To Preserve

- Five primitives remain the citizen-facing main surface: `lookup`, `resolve_location`, `submit`, `verify`, `subscribe`.
- Tool discovery must derive from registry metadata and adapter docs, not hardcoded scenario routing.
- Missing location data must trigger location-resolution reasoning when a suitable resolver exists.
- Missing required tool parameters must remain recoverable inside the agentic loop unless the source proves the request is impossible.
- Live/mock/handoff classification must follow: public API + credential = live; official or policy-mandated channel without access = shape-faithful mock; opaque forever = narrative handoff only.
- Permission UX follows Claude Code's `Select` and `feedbackConfig` pattern unless CC source proves otherwise.
- Expanded tool logs must expose normalized parameters, adapter result, citations, error detail, and correlation context.

## RALF Loop

Repeat this loop until acceptance criteria pass.

1. Research: invoke `$kosax-reference-first`, then read the relevant KOSAX docs, CC restored source, local adapter docs, official API docs, and only then secondary open-source/community references for implementation insight. For OpenAI/Codex behavior, also invoke `openai-docs`.
2. Analyze: reproduce the issue with real user-like TUI/PTY flow and full-frame captures. Inspect the entire frame sequence, not only the final screen.
3. Locate root cause: identify the exact contract boundary that allowed the abnormal flow.
4. Fix: change the root boundary with the smallest reference-grounded patch. No fallback, static special case, or symptom-only patch.
5. Verify: run targeted tests, type checks, direct curl probes where live APIs are involved, and the real-use scenario that failed. Also inspect UI/UX, interaction, backend, reasoning, tool-call, visualization, painting, and debug-inspection flow for abnormal behavior even when no exception is raised.
6. Correlate: build the LLMOps rendering-flow timeline by joining trace ids, IPC frames, tool dispatch, permission events, render commits, frame artifacts, and expanded tool logs.
7. Broaden: add or rerun adjacent citizen scenarios that exercise the same abstraction.
8. Record: update the research-source ledger, research notes, API evidence, scenario matrix, LLMOps timeline, and capture summaries.
9. Loop: continue while any UI/UX, backend, reasoning, tool-call, visualization, painting, permission, debug-inspection, or packaging flow is abnormal.

Three failed symptom fixes in a row means stop, capture the timeline, and re-evaluate the architecture.

## Scenario Coverage

Build and run broad real-use scenarios from KOSAX' ultimate goal. Include both happy paths and failure/recovery paths.

- Emergency: child fever near Hadan Station, resolve location first, then NMC emergency lookup.
- Weather/safety: Busan Saha-gu Dadae 1-dong weather, resolve location first, then KMA current/forecast flow.
- Welfare: single-parent household support lookup, MOHW live contract validation, eligibility explanation, mock application with permission and receipt.
- Government24: civil-affairs submit flow with identity/permission gate, user-visible confirmation, receipt.
- Hometax: tax-related mock flow with verify/certificate gate, policy citation, receipt or honest handoff.
- Payment/penalty: fines/tax/utility-like mock or handoff flow without pretending opaque private APIs are known.
- Healthcare: HIRA/NMC/NFA119 lookup flows with official parameters and visible details.
- Road safety: KOROAD hazard lookup with official parameters and inspectable result.
- Identity/certificate: mobile ID, simple auth, certificate mocks with strict mock boundaries.
- Subscription: public safety or utility alert subscription with permission and revocation visibility.
- Error recovery: ambiguous place, missing coordinates, invalid params, upstream zero result, upstream auth failure, timeout, refusal circuit breaker.
- Permission variants: allow once, allow session, deny, cancel, Tab feedback amendment.
- Transcript/debug: expand tool call details and verify the user can inspect what happened.

Add more scenarios when the ultimate goal implies a realistic citizen workflow that is not covered.

## Verification Gates

Do not claim final readiness until applicable gates pass.

- `uv run ruff check src tests scripts`
- `uv run pytest -m "not live"`
- `cd tui && bun run typecheck`
- `cd tui && bun test`
- Direct `curl` evidence for every touched live adapter, with secrets redacted.
- Real-use PTY matrix under `specs/2773-rollback-debug-infra/captures/`.
- For any `tui/src/**` change, perform the AGENTS.md TUI verification chain with frame snapshots and visual artifacts required by the active spec.
- Inspect frame artifacts for intermediate abnormal states, not only final state.
- Inspect expanded tool/debug logs for parameter correctness, adapter response fidelity, error visibility, and follow-up reasoning.
- Inspect the LLMOps rendering-flow timeline that joins LLM chunks, IPC frames, tool dispatch, permission frames, render commits, frame captures, and expanded logs.
- Record non-exception abnormal flows as failures in the scenario audit.
- Confirm no committed evidence leaks credentials or personal data.

If a full gate is blocked, state the exact blocker and run the strongest safe subset. Do not mark the goal complete.

## Acceptance Criteria

The goal is complete only when all of these are true:

- KOSAX still implements the CC harness migration thesis with only the sanctioned swaps.
- The five primitive abstraction works across the scenario matrix.
- Recoverable tool validation errors do not terminate the agentic loop.
- Missing data is resolved through available tools or surfaced as structured citizen input, not guessed or silently abandoned.
- Permission UX is CC-style Select with Up/Down, Enter, Esc, and Tab feedback.
- Permission decisions propagate to backend behavior correctly.
- Tool errors render as visible error states and remain inspectable in expanded logs.
- Non-exception abnormal flows are treated as failures and fixed: stale UI state, broken interaction, stuck backend continuation, illogical model recovery, invisible tool details, or incoherent repaint.
- Debugging infrastructure provides enough evidence to reconstruct each tested user turn from input to final render.
- LLMOps rendering-flow evidence reconstructs each tested turn from user input through model chunks, IPC frames, tool calls, permission events, render commits, frame snapshots, and final visible output.
- Live adapters use official endpoint/parameter contracts proven by curl.
- Mock adapters are shape-faithful, evidence-graded, and clearly not live.
- No hardcoded fallback, static routing, static policy, or hallucinated API behavior is introduced.
- TUI, backend, reasoning, tool-call, visualization, painting, logs, docs, and packaging gates are normal.
- The final status names the skill-driven research-source ledger and every verification command with whether it passed, failed, or was blocked.

## First Turn Instruction

Start by invoking `$kosax-reference-first` and reading the source-of-truth hierarchy above. Then write the research-source ledger and reference bootstrap note before editing anything. Reproduce the highest-risk current flows with real-use TUI/PTY captures, starting with permission flow and public-service adapter parameter recovery. Continue the RALF loop until KOSAX is packaging-ready by the acceptance criteria, or stop only when a blocker is proven with exact file references, command output, and evidence.
