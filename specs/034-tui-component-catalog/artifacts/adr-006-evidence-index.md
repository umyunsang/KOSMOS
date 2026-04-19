# ADR-006 Part D Evidence Index

**Source**: `docs/adr/ADR-006-cc-migration-vision-update.md § Part D` (lines 181–213).
**Consumers**: T012 (permissions/safety DISCARD citations), T014 (root.dev-ui + root.misc DISCARDs), T033 (DISCARD audit).

## 1 · Part D-1 — Intentionally NOT migrated (4 categories)

Every DISCARD row citing Part D-1 MUST start `Rationale = "ADR-006 Part D-1 — <category>: <specific subcase>"`.

### Category D-1.a · Dev-only slash commands

Rationale boilerplate: `ADR-006 Part D-1 — Dev-only slash commands: citizens do not ship PRs.`

Not in `src/components/` directly, but downstream references in components may trigger DISCARD:

- Any component tied to `/commit`, `/pr_comments`, `/review`, `/issue`, `/install-github-app`, `/doctor`, `/heapdump`, `/vim`, `/model`, `/config`.

### Category D-1.b · Anthropic-platform surfaces

Rationale boilerplate: `ADR-006 Part D-1 — Anthropic-platform surface: KOSMOS delegates to FriendliAI + data.go.kr, which expose different contracts.`

CC component files that plumb into Anthropic OAuth / billing / prompt hubs:

- `AutoUpdater.tsx`, `AutoUpdaterWrapper.tsx`, `NativeAutoUpdater.tsx`, `PackageManagerAutoUpdater.tsx` → Anthropic release channel surfaces (KOSMOS uses `uv` / `pip`).
- `ConsoleOAuthFlow.tsx`, `ApproveApiKey.tsx`, `ChannelDowngradeDialog.tsx` → Anthropic Console OAuth + API key flow (irrelevant for KOSMOS FriendliAI key handling, which lives in env-var layer).
- `AwsAuthStatusBox.tsx` → Bedrock provider status (not a FriendliAI provider).
- `DesktopHandoff.tsx`, `DesktopUpsell/*`, `ClaudeInChromeOnboarding.tsx`, `IdeAutoConnectDialog.tsx`, `IdeOnboardingDialog.tsx`, `IdeStatusIndicator.tsx`, `ShowInIDEPrompt.tsx` → Claude Desktop / VS Code / IDE cross-sells.
- `BridgeDialog.tsx`, `buddy*`, `ConsoleOAuthFlow.tsx`, `ClaudeMdExternalIncludesDialog.tsx` → Anthropic platform bridges.
- `GlobalSearchDialog.tsx`, `HistorySearchDialog.tsx`, `QuickOpenDialog.tsx` (IF they target `~/.claude` cross-session history — CC dev ergonomic; citizen sessions have shorter lifecycle).
- `SentryErrorBoundary.ts` → Sentry is Anthropic's telemetry vendor; KOSMOS uses local OTEL + Langfuse (Spec 021).

### Category D-1.c · Migration helpers

Rationale boilerplate: `ADR-006 Part D-1 — Migration helper: CC-specific settings migrations; KOSMOS has no analog.`

- Not in `src/components/`; flagged only if a component renders the output of `src/migrations/*`.

### Category D-1.d · Domain-mismatch modules

Rationale boilerplate: `ADR-006 Part D-1 — Domain mismatch: <voice|vim|plugins> are developer ergonomics with no citizen-domain use case.`

Components tied to `src/voice/`, `src/vim/`, `src/plugins/`:

- `VimTextInput.tsx` → vim-mode text input; `Shift+Tab`/`Esc` gauntlet suffices for citizens.

### Category D-1.e · Dev-UI surfaces (implicit Part D-1)

Rationale boilerplate: `ADR-006 Part D-1 — Developer-domain UI surface: <X> diagnostic/telemetry; KOSMOS citizen flows do not expose it.`

- `DevBar.tsx`, `DevChannelsDialog.tsx`, `DiagnosticsDisplay.tsx`, `MemoryUsageIndicator.tsx`, `RemoteCallout.tsx`, `RemoteEnvironmentDialog.tsx`, `LogSelector.tsx` → developer observability; KOSMOS OTEL + Langfuse server-side only.
- `TeleportError.tsx`, `TeleportProgress.tsx`, `TeleportRepoMismatchDialog.tsx`, `TeleportResumeWrapper.tsx`, `TeleportStash.tsx` → Anthropic's "teleport session" multi-device hand-off; KOSMOS has no multi-device story.

## 2 · Part D-3 — KOSMOS-original surfaces (no CC analog)

Rationale boilerplate: `ADR-006 Part D-3 — KOSMOS-original surface: <X>; no CC analog exists.`

Not relevant for CC `src/components/` rows (those all have CC counterparts by definition). Applies only to KOSMOS-native `src/kosmos/*` surfaces which are **out of scope for the verdict matrix** per FR-033. **No catalog row should cite Part D-3** unless triangulating a reverse-direction question ("does KOSMOS X have a CC analog?" — not this Epic's concern).

## 3 · Domain-mismatch rationales (free-text prefix)

Rationale prefix: `Domain mismatch: <reason>`.

Used when the component has a CC counterpart but no citizen equivalent AND the reason does not cleanly fit one of the D-1 subcategories. Examples:

- `Domain mismatch: GitHub-specific workflow; KOSMOS ministries do not ship PRs.` (for `WorkflowMultiselectDialog.tsx` if it targets GitHub Actions).
- `Domain mismatch: Team/seat management for enterprise CC; KOSMOS is single-citizen per session.` (for `teams/*`).
- `Domain mismatch: Git-tree worktree management; KOSMOS has no source-control surface.` (for `WorktreeExitDialog.tsx`, `grove/*`).
- `Domain mismatch: skill-authoring surface for Claude Code users; KOSMOS tool adapters are authored server-side in Python.` (for `skills/*`, `SkillImprovementSurvey.tsx`).
- `Domain mismatch: Anthropic feedback pipeline; KOSMOS has no public feedback intake.` (for `Feedback.tsx`, `FeedbackSurvey/*`).

## 4 · Classification hints (Part D-3 carve-outs — `src/kosmos/`)

Per FR-033: these do NOT appear in the catalog. Listed here so classifiers know to skip them if they surface via grep:

- `src/kosmos/safety/` — 8 files (PIPA redactor, prompt-injection defence).
- `src/kosmos/security/` — Specs 024/025 V1–V6 validator.
- `src/kosmos/primitives/` — Spec 031 submit/subscribe/verify.
- `src/kosmos/tools/{geocoding,hira,kma,koroad,nfa119,nmc}/` — ministry adapter tree.

These are legitimate KOSMOS extensions with no CC counterpart. If a future reviewer asks "where is `safety` in the catalog?" the answer is "Part D-3 carve-out; not a migration target."

## 5 · Prefix allow-list (enforced by I4 / T033 audit)

Every DISCARD row's `Rationale` column MUST start with **exactly one** of:

1. `ADR-006 Part D-1` (with subcategory wording from §1 above)
2. `ADR-006 Part D-3` (rare — only if reverse-triangulating a KOSMOS-original that somehow lands in the matrix)
3. `Domain mismatch:` (free-text beyond D-1 / D-3)

Validator (`/speckit-analyze` T034) greps the Verdict column for `DISCARD` and asserts the Rationale column begins with one of the three prefixes. Violations fail the gate.
