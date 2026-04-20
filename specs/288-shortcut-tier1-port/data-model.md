# Phase 1 · Data Model — Shortcut Tier 1 Port

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Entities

### 1. `KeybindingContext` (enum)

**Purpose**: Names the input-handling scope a binding applies in. The resolver (D7) consults contexts in precedence order.

**Shape** (TypeScript literal union; port of CC `schema.ts` L12-L32 narrowed):

```ts
export const KEYBINDING_CONTEXTS = [
  'Global',          // active everywhere unless a higher-precedence context claims the chord
  'Chat',            // when InputBar has focus
  'HistorySearch',   // when ctrl+r overlay is open
  'Confirmation',    // when a PermissionGauntletModal/ConsentPrompt is open
] as const
export type KeybindingContext = typeof KEYBINDING_CONTEXTS[number]
```

**Contexts deliberately omitted from CC's full list**: `Autocomplete`, `Help`, `Transcript`, `Task`, `ThemePicker`, `Settings`, `Tabs`, `Attachments`, `Footer`, `MessageSelector`, `DiffDialog`, `ModelPicker`, `Select`, `Plugin` — none are live in KOSMOS Phase 2. Tier 2/3 ports (Epics E / post-launch) will broaden the enum.

### 2. `TierOneAction` (enum)

**Purpose**: Names the six behaviours this spec introduces. Chord strings (`ctrl+c`, `shift+tab`, etc.) are *not* part of the action identity — they can be remapped (FR-026) — so actions are referenced by name everywhere outside `defaultBindings.ts`.

```ts
export const TIER_ONE_ACTIONS = [
  'agent-interrupt',         // ctrl+c default (reserved)
  'session-exit',            // ctrl+d default (reserved)
  'draft-cancel',            // escape default, Chat context
  'history-search',          // ctrl+r default, Global context
  'history-prev',            // up default, Chat context
  'history-next',            // down default, Chat context
  'permission-mode-cycle',   // shift+tab default (meta+m on Windows pre-VT)
] as const
export type TierOneAction = typeof TIER_ONE_ACTIONS[number]
```

### 3. `KeybindingEntry`

**Purpose**: Immutable record describing one binding in the registry.

**Shape**:

```ts
export type KeybindingEntry = {
  action: TierOneAction
  default_chord: ChordString              // e.g., "ctrl+c"
  effective_chord: ChordString | null     // null = disabled by user override
  context: KeybindingContext
  description: string                     // citizen-readable (ko + en)
  remappable: boolean                     // false for reserved (agent-interrupt, session-exit)
  reserved: boolean                       // true ⟹ remappable=false
  mutates_buffer: boolean                 // gate on useKoreanIME().isComposing when true
}
```

**Invariants**:
- `reserved === true` ⟹ `remappable === false`.
- `effective_chord === null` is allowed **only when** `reserved === false` (FR-028).
- `default_chord` is a valid chord per `parser.ts` grammar (enforced at registry-build time).

**Source of truth**: built at TUI launch by merging `DEFAULT_BINDINGS` (seed) with `loadUserBindings()` output; in-memory immutable map keyed by `action`.

### 4. `ChordString`

**Purpose**: Canonical key-combination syntax. Reused verbatim from CC `parser.ts` / `shortcutFormat.ts`.

**Grammar** (EBNF):

```ebnf
chord       = modifier-seq key
modifier-seq = { modifier "+" }
modifier    = "ctrl" | "shift" | "alt" | "meta"
key         = letter | digit | special
special     = "tab" | "enter" | "escape" | "up" | "down" | "left" | "right"
            | "pageup" | "pagedown" | "home" | "end" | "space" | "backspace" | "delete"
            | "f1" .. "f12"
```

**Canonicalisation**: Modifier order is `ctrl → shift → alt → meta`, lower-cased; letters lower-cased; `parser.ts` enforces.

**Examples**: `ctrl+c`, `shift+tab`, `ctrl+shift+p`, `escape`, `up`.

### 5. `UserOverrideFile`

**Purpose**: Optional citizen-editable JSON file at `~/.kosmos/keybindings.json`.

**Shape** (see contracts/user-override.schema.json for the canonical JSON Schema):

```jsonc
{
  // <chord> : <action> | null
  "ctrl+r": null,            // disable history-search
  "ctrl+f": "history-search" // remap history-search to ctrl+f
}
```

**Validation** (enforced by `validate.ts`):
- File missing or unreadable → registry uses defaults only; parse error logged (FR-023).
- File parses but shape invalid (e.g., object-of-object, non-string key, non-string-non-null value) → defaults only; error logged (FR-024).
- Attempted remap of a reserved action → entry rejected, warning logged; defaults remain (FR-027).
- Chord not in grammar → entry rejected, warning logged; defaults remain.

### 6. `ChordEvent`

**Purpose**: Runtime input event handed to the resolver.

**Shape**:

```ts
export type ChordEvent = {
  raw: string              // raw byte or key name from Ink
  chord: ChordString       // normalised by parser
  ctrl: boolean
  shift: boolean
  alt: boolean
  meta: boolean
  timestamp: number        // performance.now() — for ctrl+c double-press window
}
```

### 7. `ResolutionResult`

**Purpose**: Output of the resolver; drives action dispatch and observability.

**Shape**:

```ts
export type ResolutionResult =
  | { kind: 'dispatched'; action: TierOneAction; context: KeybindingContext }
  | { kind: 'blocked'; action: TierOneAction; reason: 'ime-composing' | 'buffer-non-empty' | 'permission-mode-blocked' | 'consent-out-of-scope' }
  | { kind: 'no-match' }                            // pass-through to lower layer
  | { kind: 'double-press-armed'; action: TierOneAction; expires_at: number }  // ctrl+c arm
  | { kind: 'double-press-fired'; action: TierOneAction }                       // second ctrl+c within window
```

## Relationships

```text
UserOverrideFile  ─┐
                   ├─► loadUserBindings ─► Merge(DEFAULT_BINDINGS, overrides) ─► Registry: Map<TierOneAction, KeybindingEntry>
DEFAULT_BINDINGS  ─┘                                                                          ▲
                                                                                              │
                                                                                              │
ChordEvent ─► resolver ─► (look up by effective_chord) ─► ResolutionResult
                ▲
                ├── useKoreanIME.isComposing  (gate)
                ├── permission-mode-blocked (from ModeCycle)
                └── consent-out-of-scope    (from memdir USER consent check)
```

## State transitions

### Double-press ctrl+c (FR-013)

```text
[idle] ──ctrl+c, no active loop──► [armed(expires_at=now+2s)]
[idle] ──ctrl+c, active loop────► [dispatched(agent-interrupt)]
[armed] ──ctrl+c, within 2s─────► [dispatched(session-exit)]
[armed] ──timeout (2s elapsed)──► [idle]
[armed] ──any other key─────────► [idle]
```

### Permission-mode cycle (FR-008, FR-009)

Cycle is delegated entirely to Spec 033's `ModeCycle.tsx` — this spec only emits the cycle request. Blocking behaviour and irreversible-action flag live in Spec 033's state machine; resolver receives either `{cycled: true, new_mode}` or `{cycled: false, reason}` and emits `ResolutionResult` accordingly.

### History cursor (FR-017, FR-018)

```text
[buffer=empty, cursor=null] ──up, history size ≥ 1──► [buffer=H[n-1], cursor=n-1]
[buffer=empty, cursor=null] ──up, history empty────► [buffer=empty, cursor=null]  (no-op, no error)
[buffer=H[i], cursor=i]     ──up, i > 0─────────────► [buffer=H[i-1], cursor=i-1]
[buffer=H[i], cursor=i]     ──down, i < n-1────────► [buffer=H[i+1], cursor=i+1]
[buffer=H[i], cursor=i]     ──down, i = n-1────────► [buffer=empty, cursor=null]  (return to present)
[buffer=<typed text>, cursor=null] ──up────────────► [unchanged]  (FR-017 pass-through)
```

## Observability fields (FR-033, FR-034)

Each successful Tier 1 dispatch emits an OTel span with attributes:

| Attribute | Type | Example | Notes |
|---|---|---|---|
| `kosmos.tui.binding` | string | `agent-interrupt` | TierOneAction name |
| `kosmos.tui.binding.context` | string | `Global` | KeybindingContext |
| `kosmos.tui.binding.chord` | string | `ctrl+c` | effective chord at dispatch |
| `kosmos.tui.binding.reserved` | bool | `true` | from KeybindingEntry |

Blocked dispatches emit the same span with an additional:

| Attribute | Type | Example |
|---|---|---|
| `kosmos.tui.binding.blocked.reason` | string | `ime-composing` |

Reserved-action dispatches additionally write a `ToolCallAuditRecord` (Spec 024) with event types `user-interrupted` or `session-exited`.
