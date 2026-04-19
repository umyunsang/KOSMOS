# Owning-Epic Lookup Table

**Evidence**: `artifacts/epic-state-2026-04-20.json` (GraphQL-verified 2026-04-20, AGENTS.md GraphQL-only rule satisfied).
**Consumers**: T010–T014 (owning-Epic column population), T031 (taskstoissues re-parent logic), T033 (closed-Epic rationale audit).

## 1 · Closed set (FR-003)

| id | issue | state | title | closure_delegate |
|---|---|---|---|---|
| M | #1310 | OPEN | Epic M — TUI component catalog migration | — (self) |
| B | #1297 | **CLOSED** | Permission v2 — PermissionMode spectrum + persistent rule store | M #1310 |
| A | #1298 | **CLOSED** | IPC stdio hardening — structured frames + backpressure + reconnect + replay | M #1310 |
| C | #1301 | OPEN | Ministry Specialist Workers — 출산 보조금 / 건강보험 / 교통 | — |
| D | #1299 | OPEN | Context Assembly v2 — memdir User tier | — |
| E | #1300 | OPEN | Korean IME — composition-aware shortcut gating + Hangul width | — |
| H | #1302 | OPEN | Onboarding + brand port (binds ADR-006 A-9) | — |
| I | #1303 | OPEN | Shortcut Tier 1 port (binds ADR-006 A-10) | — |
| J | #1307 | OPEN | Cost/Token HUD — citizen-visible FriendliAI + data.go.kr quota display | — |
| K | #1308 | OPEN | Settings TUI dialog — language · permission mode · theme picker | — |
| L | #1309 | OPEN | Notifications surface — out-of-band event toasts | — |

## 2 · Closed-Epic rule (research §R3, catalog-row-schema §2.2)

When a logical-owning Epic is CLOSED:

- **Fully delivered** by the closed Epic's ship (e.g., `PermissionGauntletModal.tsx` delivered by #1441):
  - `Verdict = PORT`, `Owning Epic = <id> #<issue> (closed)`, `Rationale = "implementation complete; delivered by #<PR>"`, `Task sub-issue = —`, `KOSMOS target = tui/src/components/coordinator/PermissionGauntletModal.tsx`.
- **TUI-side rewrite still needed** after the closed Epic's ship:
  - `Verdict = REWRITE`, `Owning Epic = <id> #<issue> (closed)`, `Task sub-issue = re-parented to Epic M #1310` at T031 (FR-026 exception; invariant I16).

## 3 · Family → typical owning Epic (hint table, T010–T014 overrides allowed)

| Family | Typical owning Epic | Rationale |
|---|---|---|
| `design-system`, `ui`, `Spinner`, `LogoV2`, `StructuredDiff`, `diff`, `HighlightedCode`, `CustomSelect` | H #1302 (brand port) | design-system tokens + Logo/splash + spinners all derive from ADR-006 A-9 brand vocabulary |
| `messages` | D #1299 + M #1310 split | message-rendering envelope = D (context assembly); streaming shell + list = M (TUI harness) |
| `PromptInput` | E #1300 | Korean IME composition safety is the Epic-E contract |
| `HelpV2`, `hooks` (UI), `memory` (UI) | M #1310 | harness-level help + hook-call rendering + /memory surfaces are MVP harness concerns |
| `shell`, `ClaudeCodeHint` | M #1310 / DISCARD (CC-specific) | shell executor surfaces mostly DISCARD; `ClaudeCodeHint` → DISCARD per D-1.b (Anthropic upsell) |
| `permissions`, `TrustDialog`, `ManagedSettingsSecurityDialog`, `sandbox`, `Passes` | B #1297 (closed) | permission spectrum shipped 2026-04-19 PR #1441; see §2 closed-Epic rule |
| `agents`, `teams`, `grove` | M #1310 / DISCARD | agents = multi-agent swarm HUD (M); teams/grove = enterprise seat mgmt → DISCARD domain mismatch |
| `mcp` | M #1310 / mixed | MCP client surfaces may PORT if harness-level; server-config dialogs mostly DISCARD (dev-only) |
| `skills` | DISCARD (domain mismatch) | skill authoring is for CC users; KOSMOS adapters live server-side in Python |
| `tasks` | M #1310 | TaskList rendering is harness-level; binds to Sub-Issues API v2 awareness |
| `wizard` | H #1302 | onboarding-adjacent wizard flows |
| `DesktopUpsell` | DISCARD (D-1.b) | Anthropic Desktop upsell, not a citizen concern |
| `FeedbackSurvey` | DISCARD (domain mismatch) | Anthropic feedback pipeline |
| `LspRecommendation` | DISCARD (D-1.e) | LSP is developer-tool, not citizen-facing |
| `Settings` | K #1308 | Settings TUI dialog is Epic K's scope |
| `root.logo-wordmark` | H #1302 | brand port territory |
| `root.dialogs` | case-by-case (H/K/J/L for citizen dialogs; DISCARD for Anthropic platform) | per-dialog classification |
| `root.shortcuts` | I #1303 | shortcut Tier 1 is Epic I's scope |
| `root.dev-ui` | DISCARD (D-1.b/D-1.e bulk) | AutoUpdater × 4, DevBar, Diagnostics, Sentry, etc. |
| `root.onboarding` | H #1302 | `Onboarding.tsx` is the Epic H entry point |
| `root.misc` | mixed (M / D / DISCARD) | streaming message pipeline (M), context cards (D), teleport surfaces (DISCARD D-1.b) |

## 4 · Validation invariants (T018, T032, T034)

- **I2** (FR-026): A REWRITE verdict whose `owning_epic` is CLOSED → `closure_delegate = M #1310`; Task sub-issue created on M, not on B/A.
- **FR-003** (catalog-row-schema §3.4): Every `Owning Epic` column value must literally match `/^[A-M] #\d{4}( \(closed\))?$/`.
- **I16** (data-model.md §1.10): For non-closed non-M REWRITE rows, `TaskSubIssue.parent_epic == CatalogRow.owning_epic` (FR-026).
