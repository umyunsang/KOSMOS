# Decision Log — UI Residue Cleanup (Epic β · #2293)

**Date**: 2026-04-29
**Authority**: AGENTS.md § CORE THESIS · `.specify/memory/constitution.md § II` · research.md R-1~R-5

---

## § 1 Cleanup Targets (services/api 17 + tokenEstimation)

| File | Importers | Decision | Rationale |
|------|-----------|----------|-----------|
| services/api/adminRequests.ts | — | DELETE | Dead — no KOSMOS citizen use case |
| services/api/claude.ts | — | DELETE | Anthropic dispatcher — FriendliAI replaces |
| services/api/client.ts | — | DELETE | Anthropic HTTP client — FriendliAI replaces |
| services/api/errorUtils.ts | — | DELETE | Anthropic error utils — dead |
| services/api/errors.ts | — | DELETE | Anthropic error types — dead |
| services/api/filesApi.ts | — | DELETE | Claude Files API — no KOSMOS equivalent |
| services/api/firstTokenDate.ts | — | DELETE | Dead analytics |
| services/api/grove.ts | — | DELETE | Anthropic internal service — dead |
| services/api/logging.ts | — | DELETE | Anthropic telemetry — KOSMOS uses OTEL |
| services/api/overageCreditGrant.ts | — | DELETE | Billing/credits — dead |
| services/api/promptCacheBreakDetection.ts | — | DELETE | Anthropic prompt cache — dead |
| services/api/referral.ts | — | DELETE | Anthropic referral — dead |
| services/api/sessionIngress.ts | — | DELETE | Anthropic session ingress — dead |
| services/api/ultrareviewQuota.ts | — | DELETE | Quota management — dead |
| services/api/usage.ts | — | DELETE | Anthropic usage stats — dead |
| services/api/withRetry.ts | — | DELETE | Anthropic retry logic — KOSMOS has its own |
| services/tokenEstimation.ts | — | DELETE | Anthropic tokenizer — dead |

---

## § 2 Callsite Migrations

| Callsite | Call | Decision | Rationale |
|----------|------|----------|-----------|
| cli/print.ts | verifyApiKey + queryHaiku | DELETE | KOSMOS = FriendliAI single provider; API key verification is different |
| commands/insights.ts | queryWithModel | DELETE | Developer insights — not a citizen use case |
| commands/rename/generateSessionName.ts | queryHaiku | DELETE | Dead or migrate — decision on inspection |
| components/Feedback.tsx | queryHaiku | DELETE | claude.ai 1P telemetry — Spec 1633 |
| services/toolUseSummary/toolUseSummaryGenerator.ts | queryHaiku | EVALUATE | Korean summary possible — check if alive |
| tools/WebFetchTool/utils.ts | queryHaiku | EVALUATE | WebFetch is MVP7 tool — check if alive |
| utils/mcp/dateTimeParser.ts | queryHaiku | DELETE | KOSMOS DateParser (MVP7) replaces |
| utils/sessionTitle.ts | queryHaiku | DELETE | Duplicate of generateSessionName |
| utils/shell/prefix.ts | queryHaiku | DELETE | Shell prefix — not a citizen use case |

---

## § 3 KOSMOS-only Tool Decisions

| Tool | Decision | Rationale | Reference |
|------|----------|-----------|-----------|
| MonitorTool | DELETE | No background tasks for citizens in KOSMOS synchronous lookup/submit flow | research.md § R-4 |
| ReviewArtifactTool | DELETE | Citizens do not review PRs | research.md § R-4 |
| SuggestBackgroundPRTool | DELETE | Citizens do not create PRs | research.md § R-4 |
| TungstenTool | DELETE | claude-code internal tool — no citizen use case identified | research.md § R-4 |
| VerifyPlanExecutionTool | DELETE | claude-code dev workflow tool | research.md § R-4 |
| WorkflowTool | DELETE | KOSMOS multi-step handled by system prompt + 4 primitive chain (Spec 022) | research.md § R-4 |

---

## § 4 ui-l2/permission.ts Decision

| File | Callers | Decision | Rationale |
|------|---------|----------|-----------|
| schemas/ui-l2/permission.ts | — | DELETE (pending caller check) | Constitution II NON-NEGOTIABLE — KOSMOS-invented permission enums must not remain in codebase |
