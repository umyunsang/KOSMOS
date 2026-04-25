# Phase 1 Data Model — P4 · UI L2 Citizen Port

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Generated**: 2026-04-25

This document defines the TS-side entities introduced by the UI L2 epic. Every entity is expressed as a Zod schema (TypeScript) so it is enforceable at runtime and so the contract files in `contracts/` can derive their shape from a single source of truth. Backend Python entities are unchanged — Spec 033 owns the permission ledger schema, Spec 027 owns the agent-mailbox payloads, Spec 035 owns the onboarding-consent record. Where this epic surfaces those entities, the TS schema is a citizen-side projection of the Python source-of-truth.

All schemas live (or will live) under `tui/src/schemas/ui-l2/`.

---

## 1 · OnboardingState

Persisted at `~/.kosmos/memdir/user/onboarding/state.json`. Owned by this epic.

```ts
import { z } from "zod";

export const OnboardingStepName = z.enum([
  "preflight",
  "theme",
  "pipa-consent",
  "ministry-scope",
  "terminal-setup",
]);

export const OnboardingStep = z.object({
  name: OnboardingStepName,
  completed_at: z.string().datetime().nullable(),
  values: z.record(z.string(), z.unknown()),
});

export const OnboardingState = z.object({
  schema_version: z.literal(1),
  started_at: z.string().datetime(),
  language: z.enum(["ko", "en"]).default("ko"),
  steps: z.array(OnboardingStep).length(5),
  current_step_index: z.number().int().min(0).max(5),
});

export type OnboardingState = z.infer<typeof OnboardingState>;
```

**Invariants**:
- `steps.length === 5` and the order is exactly `preflight, theme, pipa-consent, ministry-scope, terminal-setup` (FR-001).
- `current_step_index === 5` means onboarding is complete; REPL is the next surface (FR-001 acceptance §1).
- `current_step_index < 5` on next launch resumes from `steps[current_step_index]` (FR-002 + edge-case "SIGINT mid-onboarding").

**State transitions**:
1. First launch → `current_step_index = 0`, all `completed_at = null`.
2. Step n complete → set `steps[n].completed_at`, increment `current_step_index`.
3. `/onboarding` re-run → reset `current_step_index = 0`; preserve prior `completed_at` for audit (do not delete).
4. `/onboarding <name>` → temporary in-memory single-step replay; the persisted state is not reset.

---

## 2 · PermissionReceipt (citizen-side projection)

Backend canonical: Spec 033 ledger. This TS entity is the read model the TUI surfaces — it never writes the ledger directly; writes go through the existing IPC envelope to the Python permission service.

```ts
export const PermissionLayer = z.union([z.literal(1), z.literal(2), z.literal(3)]);

export const PermissionDecision = z.enum([
  "allow_once",
  "allow_session",
  "deny",
  "auto_denied_at_cancel",
  "timeout_denied",
]);

export const PermissionReceipt = z.object({
  receipt_id: z.string().regex(/^rcpt-[A-Za-z0-9_-]{8,}$/),
  layer: PermissionLayer,
  tool_name: z.string().min(1),
  decision: PermissionDecision,
  decided_at: z.string().datetime(),
  session_id: z.string().min(1),
  revoked_at: z.string().datetime().nullable(),
});

export type PermissionReceipt = z.infer<typeof PermissionReceipt>;
```

**Invariants**:
- `receipt_id` comes from the backend; the TUI never mints one.
- `revoked_at` is set only via `/consent revoke`. Setting it does not delete the original record — Spec 033 ledger is append-only (FR-007, FR-021).
- Idempotency: a `revoke` request whose `receipt_id` already has `revoked_at !== null` MUST NOT produce a new ledger entry; the TUI shows a "이미 철회됨" toast (FR-021).

**Display rules** (FR-016):
- `layer === 1` → green color token + glyph `⓵`
- `layer === 2` → orange color token + glyph `⓶`
- `layer === 3` → red color token + glyph `⓷` + reinforcement notice line

---

## 3 · AgentVisibilityEntry

Live-updating row in the `/agents` panel. Streamed from the existing Spec 027 mailbox event; this entity is the TUI's rendered shape.

```ts
export const AgentState = z.enum([
  "idle",
  "dispatched",
  "running",
  "waiting-permission",
  "done",
]);

export const AgentHealth = z.enum(["green", "amber", "red"]);

export const AgentVisibilityEntry = z.object({
  agent_id: z.string().min(1),
  ministry: z.string().min(1),
  state: AgentState,
  sla_remaining_ms: z.number().int().nonnegative().nullable(),
  health: AgentHealth,
  rolling_avg_response_ms: z.number().nonnegative().nullable(),
  last_transition_at: z.string().datetime(),
});

export type AgentVisibilityEntry = z.infer<typeof AgentVisibilityEntry>;
```

**Invariants**:
- Five-state enum is canonical (proposal-iv) — adding states requires an ADR (FR-025).
- `sla_remaining_ms`, `rolling_avg_response_ms` may be `null` only while the entry is still in `dispatched` (no SLA established yet).
- Updates arrive as push events; the TUI never polls (FR-028 / SC-007).

**Swarm activation predicate** (FR-027):

```ts
export function shouldActivateSwarm(plan: { mentioned_ministries: string[]; complexity_tag: "simple" | "complex" }): boolean {
  return plan.mentioned_ministries.length >= 3 || plan.complexity_tag === "complex";
}
```

The "OR" form is canonical (migration tree D.2). Single-condition variants are rejected.

---

## 4 · SlashCommandCatalogEntry

Single source of truth for FR-014 autocomplete dropdown and FR-029 `/help` 4-group output. Static metadata, compiled at TUI build time.

```ts
export const SlashCommandGroup = z.enum([
  "session",
  "permission",
  "tool",
  "storage",
]);

export const SlashCommandCatalogEntry = z.object({
  name: z.string().regex(/^\/[a-z][a-z0-9-]*( [a-z0-9-]+)?$/),
  group: SlashCommandGroup,
  description_ko: z.string().min(1),
  description_en: z.string().min(1),
  arg_signature: z.string().nullable(),
  hidden: z.boolean().default(false),
});

export type SlashCommandCatalogEntry = z.infer<typeof SlashCommandCatalogEntry>;
```

**Invariants**:
- Each entry belongs to exactly one group (FR-029).
- `description_ko` is required; `description_en` is the FR-004 fallback.
- `hidden = true` excludes the entry from `/help` and from autocomplete (used for development-only commands).

**Initial registration set** (this epic):
- `/onboarding` and `/onboarding <step>` — group `session`
- `/lang ko|en` — group `session`
- `/consent list`, `/consent revoke <rcpt-id>` — group `permission`
- `/agents`, `/agents --detail` — group `tool`
- `/help` — group `session`
- `/config` — group `storage`
- `/plugins` — group `tool`
- `/export` — group `storage`
- `/history` (with three filter forms) — group `storage`

---

## 5 · AccessibilityPreference

Persisted at `~/.kosmos/memdir/user/preferences/a11y.json`. New path owned by this epic (D-5 in `research.md`).

```ts
export const AccessibilityPreference = z.object({
  schema_version: z.literal(1),
  screen_reader: z.boolean().default(false),
  large_font: z.boolean().default(false),
  high_contrast: z.boolean().default(false),
  reduced_motion: z.boolean().default(false),
  updated_at: z.string().datetime(),
});

export type AccessibilityPreference = z.infer<typeof AccessibilityPreference>;
```

**Invariants**:
- Each toggle is independent (FR-005). Combinations like `screen_reader=true & high_contrast=true` are valid.
- A toggle change persists within 500 ms of activation (SC-011) and re-renders dependent components.

---

## 6 · ErrorEnvelope

Wraps any failed turn for FR-012 visual differentiation.

```ts
export const ErrorEnvelopeType = z.enum(["llm", "tool", "network"]);

export const ErrorEnvelope = z.object({
  type: ErrorEnvelopeType,
  title_ko: z.string().min(1),
  title_en: z.string().min(1),
  detail_ko: z.string().nullable(),
  detail_en: z.string().nullable(),
  retry_suggested: z.boolean(),
  occurred_at: z.string().datetime(),
});

export type ErrorEnvelope = z.infer<typeof ErrorEnvelope>;
```

**Display rules** (FR-012):
- `type === "llm"` → purple accent + brain glyph
- `type === "tool"` → orange accent + wrench glyph
- `type === "network"` → red accent + signal-broken glyph

---

## 7 · UfoMascotPose

Brand entity for FR-035. Already shipped by Spec 034 token catalog; this schema only documents the rendering contract.

```ts
export const UfoMascotPose = z.enum(["idle", "thinking", "success", "error"]);
export type UfoMascotPose = z.infer<typeof UfoMascotPose>;
```

Pose-to-context binding:
- `idle` — REPL empty state, awaiting input
- `thinking` — LLM is generating, tool call in flight, or awaiting permission decision
- `success` — final answer shipped, or permission granted
- `error` — any `ErrorEnvelope` rendered, or permission denied

---

## 8 · Cross-entity relationships

```
OnboardingState
  └── AccessibilityPreference (selected in terminal-setup step)

PermissionReceipt
  └── (citizen view) referenced by /consent list, /consent revoke
  └── (export) included in /export PDF (FR-032)

AgentVisibilityEntry
  └── push-streamed via Spec 027 mailbox event channel
  └── may emit PermissionReceipt requests when entering waiting-permission state

SlashCommandCatalogEntry
  ├── consumed by autocomplete dropdown (FR-014)
  └── consumed by /help 4-group output (FR-029)

ErrorEnvelope
  └── replaces conversation block on any failed turn (FR-012)
  └── never appears in /export PDF when type === "tool" + result was rejected (FR-032 contract)
```

No circular references. No new database. All TS state is in-memory plus the two memdir JSON paths owned by this epic.
