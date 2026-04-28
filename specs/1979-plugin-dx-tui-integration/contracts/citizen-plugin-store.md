# Contract — Citizen plugin store TUI surface

**Surface**: `tui/src/commands/plugins.ts` (T066 entry point — MODIFIED) + `tui/src/components/plugins/PluginBrowser.tsx` (T065 — MINOR EXTENSION) + `tui/src/commands/plugin.ts` (singular — wiring change to be reachable).
**Trigger**: Citizen types `/plugins` in REPL OR `/plugin <subcommand>` for install/uninstall/list.
**Purpose**: Citizen-facing browser of installed plugins per migration tree § UI-E.3, with ⏺/○/Space/i/r/a key bindings and bilingual (Korean primary, English fallback) display.

---

## Slash command registration (FR-018 V1 deliverable)

`tui/src/commands.ts:133` MUST change:

```diff
-import plugin from './commands/plugin/index.js'
+import plugin from './commands/plugin.js'
```

After this swap:
- `/plugin install <name>` → `tui/src/commands/plugin.ts` (KOSMOS singular) → emits `plugin_op_request:install`.
- `/plugin uninstall <name>` → same KOSMOS singular → emits `plugin_op_request:uninstall`.
- `/plugin list` → same KOSMOS singular → emits `plugin_op_request:list` (returns synchronously to its acknowledgment surface).
- `/plugin pipa-text` → same KOSMOS singular → returns canonical SHA-256.
- `/plugins` (plural) → routes to `tui/src/commands/plugins.ts` (T066 entry — modified) → opens PluginBrowser.
- `/marketplace` → no longer aliased; either unbound (slash autocomplete shows nothing) or bound to a Korean message "marketplace browser deferred to #1820" — TBD in implementation.

The CC residue under `tui/src/commands/plugin/` directory becomes unreachable from citizen-typed slash commands. Cleanup tracked in deferred items.

---

## `/plugins` browser data flow (FR-015, FR-016, FR-019)

```
[Citizen types /plugins]
        ↓
[executePlugins(args) — tui/src/commands/plugins.ts]
        ↓
[args.sendPluginOp({ op: "request", request_op: "list", correlation_id: <C> })]
        ↓
[await args.awaitPluginOpComplete(<C>) with backing payload reassembly]
        ↓
[parsePluginListBody(completeFrame) → PluginEntry[]]
        ↓
[REPL.tsx mounts <PluginBrowser plugins={entries} ... />]
```

The `awaitPluginOpComplete` helper is a thin wrapper around the existing IPC `bridge.ts` correlation-id matcher; its implementation pattern matches the existing tool-call response correlation in Spec 1978.

---

## `PluginEntry` shape (extension to Spec 1635 T065)

```typescript
export type PluginEntry = {
  // EXISTING (Spec 1635 T065)
  id: string;                       // plugin_id
  name: string;                     // display name (catalog name)
  version: string;                  // semver
  description_ko: string;
  description_en: string;
  isActive: boolean;                // ToolRegistry._inactive shadow set state

  // NEW (this Epic — additive, backwards compatible)
  tier: 'live' | 'mock';
  layer: 1 | 2 | 3;
  trustee_org_name: string | null;  // null when processes_pii=false
  install_timestamp_iso: string;
  search_hint_ko: string;
  search_hint_en: string;
};
```

Backwards compatibility: existing Spec 1635 T065 PluginBrowser tests using only the original 6 fields continue to pass; the 6 new fields are optional from the test fixture's perspective.

---

## Visual layout (preserves Spec 1635 T065 ≥ 90 % fidelity)

```
✻ KOSMOS 플러그인 (3 installed)

  ⏺  ›  seoul-subway     v1.0  [Live]  ⓵  서울 지하철 도착 정보 조회 …       (지금 활성)
  ○      post-office     v0.5  [Live]  ⓶  우편물 추적 — 우정사업본부            (비활성)
  ⏺      nts-homtax      v0.2  [Mock]  ⓶  세금 신고 — NTS (Mock, 시연용)         (지금 활성)

  Space 활성 토글 · i 상세 · r 제거 · a 스토어 (deferred)
  Esc · 닫기
```

Column allocation (extends existing 3-column Spec 1635 layout):

| Column | Width | Source |
|---|---|---|
| Status glyph (⏺/○) | 3 chars | `isActive` |
| Cursor + Name | 24 chars | `name`; `›` prefix when selected |
| Version | 6 chars | `v${version}` |
| Tier badge | 6 chars | `[Live]` or `[Mock]` |
| Layer glyph | 3 chars | `⓵` / `⓶` / `⓷` colored green/orange/red |
| Description | flex-grow | `description_ko` (or `_en` if `KOSMOS_TUI_LOCALE=en`) |
| Active hint | right-aligned | `(지금 활성)` / `(비활성)` |

The keybinding hint line below the list is preserved from Spec 1635; updated to add `r 제거` and `a 스토어 (deferred)`.

---

## Keystroke contract (FR-016)

| Key | Action |
|---|---|
| `↑` / `↓` | Move cursor (existing Spec 1635 behavior) |
| `Space` | Visual toggle of `isActive` glyph (in this Epic — does not round-trip to backend per R-3/R-4 verdict) |
| `i` / `I` | Open detail view modal (sub-component, future implementation may extend the existing onDetail callback) |
| `r` / `R` | Open confirmation modal → on accept, emit `plugin_op_request:uninstall` |
| `a` / `A` | Render Korean message "스토어 브라우저는 #1820 에서 작업 중입니다 (deferred)" — never an empty no-op |
| `Esc` | Dismiss browser (existing Spec 1635 behavior) |

The existing `PluginBrowser.tsx:83-111` `useInput` handler already covers all 6 keys; only the `onMarketplace()` callback's body changes (currently calls a no-op marketplace open; new behavior renders the deferred message).

---

## Detail view (`i` keystroke)

Renders a sub-modal with:

```
✻ seoul-subway v1.0 [Live]

  티어 (Tier):                live
  권한 레벨 (Permission):      Layer 1 (green ⓵)
  PII 처리 (PII):              아니오 (no)
  수탁 기관 (Trustee org):     —
  설치 일시 (Installed):        2026-04-28T12:00:00Z
  검색어 (Search hints):
    ko:  지하철 도착 시간 강남역
    en:  subway arrival time station

  설명 (Description):
    서울 지하철 도착 정보 조회 — 서울시 공공데이터 포털 API 를 통해
    실시간 지하철 도착 정보를 제공합니다.

  Esc · 닫기
```

For `processes_pii=true` plugins, an additional section:

```
  PIPA §26 수탁자 동의 해시 (acknowledgment SHA-256):
    a3b7…f9e2

  자세한 정책: docs/plugins/security-review.md
```

---

## Remove confirmation modal (`r` keystroke)

```
⚠  플러그인 제거 확인

  seoul-subway v1.0 을 제거하시겠습니까?
  ⏺  설치 디렉터리: ~/.kosmos/memdir/user/plugins/seoul_subway/
  ⏺  영수증 (uninstall) 이 ~/.kosmos/memdir/user/consent/ 에 추가됩니다.

  [Y 제거 / N 취소]
```

On Y: emits `plugin_op_request:uninstall`. The browser blocks the row's interaction (renders "(제거 중…)" placeholder) until the matching `plugin_op_complete` frame arrives. On success, the row disappears from the list. On failure, an error toast renders and the row stays.

---

## In-flight install indicator (FR-019)

When a `plugin_op_progress` frame is observed while the browser is open with a known plugin name not yet in the list, render a placeholder row:

```
  ⏳  ›  <name>           ...     [...]  ⓪  (설치 중… 단계 N/7)
```

The placeholder converts to a real row when `plugin_op_complete:success` arrives (browser re-fetches the list automatically after each terminal `plugin_op_complete`).

---

## Localization (FR-024)

- All citizen-facing strings (column labels, key bindings hint, detail labels, confirmation modals, deferred messages) are bilingual:
  - Korean primary text rendered first.
  - English fallback in parentheses or as secondary line.
- `KOSMOS_TUI_LOCALE=en` environment variable suppresses Korean primary, English-only mode.
- Source code identifiers stay English per AGENTS.md hard rule.

---

## OTEL surface emission

`tui/src/commands/plugins.ts:executePlugins` continues to emit `kosmos.ui.surface=plugins` (existing Spec 1635 FR-037).

The new `awaitPluginOpComplete` round-trip wraps the existing IPC frame plumbing — no new TUI-side OTEL needed; backend's `kosmos.plugin.list` span (R-1) covers it.

---

## Test seams

### bun test (PluginBrowser.test.tsx + plugins.test.ts)
1. `renders 3 entries with mixed tier and layer`: fixture entries → expected glyph + badge + color combinations.
2. `Space toggles isActive visually`: Space keystroke → `isActive` flips; no IPC emit (R-3/R-4).
3. `r emits uninstall frame`: r keystroke → confirmation → Y → `args.sendPluginOp({request_op: "uninstall", name})`.
4. `a renders deferred message`: a keystroke → onMarketplace called → Korean deferred string visible in next render.
5. `i opens detail with PII fields`: fixture with `processes_pii=true` + `trustee_org_name` → detail modal shows acknowledgment SHA-256.
6. `executePlugins round-trips list request`: mock IPC → assert correlation ID + frame shape; mock complete frame → assert PluginEntry[] parsed.

### PTY (smoke-1979.expect)
1. Type `/plugins` → expect Korean header "✻ KOSMOS 플러그인" within 2 s.
2. Send `r` → expect confirmation modal → send `Y` → expect "(제거 중…)" placeholder.
3. Wait for terminal frame → expect row removal.

---

## Citations

- `tui/src/components/plugins/PluginBrowser.tsx:1-171` (Spec 1635 T065)
- `tui/src/commands/plugins.ts:1-52` (Spec 1635 T066 — current env-var stub)
- `tui/src/commands/plugin.ts:1-209` (KOSMOS singular — current orphaned)
- `tui/src/commands.ts:133` (CC residue import — to be swapped)
- `docs/requirements/kosmos-migration-tree.md § UI-E.3` (key binding mandate)
- `docs/requirements/kosmos-migration-tree.md § UI-C.1` (layer color glyph mandate)
