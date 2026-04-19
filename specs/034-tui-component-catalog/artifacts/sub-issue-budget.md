# T016 · Sub-Issue Budget Pre-Flight (FR-025, SC-007)

**Hard cap**: Epic M Task sub-issues ≤ 90 (excluding `[Deferred]`-prefixed).
**Partition baseline**: research §R4 + T016.

## 1 · REWRITE Tasks projected from committed catalog

Counts from `docs/tui/component-catalog.md` (2026-04-20 snapshot, 230 rows, 389 files).

| Owning Epic | REWRITE rows | Goes to Epic M? | Notes |
|---|---:|---|---|
| M #1310 | 15 | YES (M direct) | harness-level catalog + brand + IME + coordinator HUD surfaces |
| B #1297 (closed) | 3 | YES (re-parent per §R3) | `permissions/*` aggregated + `TrustDialog` rewrites still needed on TUI side |
| A #1298 (closed) | 0 | — | no CC component rows landed with A as owner |
| H #1302 | 13 | no | brand port (Onboarding, LogoV2, FastIcon, chrome, wizard, tokens values) |
| K #1308 | 8 | no | Settings TUI (config + status + usage + theme + language + managed-settings + invalid-config) |
| D #1299 | 4 | no | context assembly (suggestions, visualization) + memory + compact |
| J #1307 | 4 | no | Cost HUD (cost-threshold, stats, status-line, token-warning) |
| E #1300 | 3 | no | IME composition gate — `PromptInput/*` aggregated + `BaseTextInput` + `TextInput` |
| I #1303 | 2 | no | shortcut Tier 1 aggregated + `KeybindingWarnings` |
| L #1309 | 1 | no | notifications (`StatusNotices`) |
| **Total REWRITE rows** | **53** | — | — |

### M-bound REWRITE Task sub-issues

15 (M direct) + 3 (re-parented from B closed) = **18**.

### Non-M REWRITE Task sub-issues (FR-026: NOT counted against M 90-cap)

35 distributed across H/K/D/J/E/I/L = **35**.

## 2 · Existing Epic M Task sub-issues (from `specs/034-tui-component-catalog/artifacts/taskstoissues-run.json`)

- **37 Tasks** materialized at `/speckit-taskstoissues` run (T001–T037 → issues #1442–#1478). Not `[Deferred]`-prefixed.
- **6 Deferred** follow-ups (rows 8, 10, 11, 12, 13, 16 from spec.md) → issues #1479–#1484. `[Deferred]`-prefixed (EXCLUDED from 90-cap per FR-025).

## 3 · Post-T031 Epic M projection

| Bucket | Count |
|---|---:|
| Existing T001–T037 non-`[Deferred]` | 37 |
| Catalog-derived REWRITE (M-direct) | 15 |
| Catalog-derived REWRITE (re-parented from B closed) | 3 |
| **Epic M non-`[Deferred]` total after T031** | **55** |
| Epic M `[Deferred]`-prefixed follow-ups | 6 |
| **Buffer to 85 (early-warning)** | **30** |
| **Buffer to 90 (hard cap)** | **35** |

**Conclusion**: projection = **55** ≤ 85 early-warning threshold. Well under the FR-025 hard cap of 90.

**No aggregation escalation required** per FR-027. Current aggregation already collapses:

- `PromptInput/*` (21 files → 1 REWRITE Task on E #1300)
- `permissions/*` (50 files → 1 REWRITE Task re-parented from B closed to M)
- `agents/*` (14 REWRITE files → 1 REWRITE Task on M)
- `tasks/*` (11 REWRITE files → 1 REWRITE Task on M)
- `messages/*`, `LogoV2/*`, `Spinner/*` (kept per-file — REWRITE counts below 11 each)

## 4 · Non-M Epic receiving Tasks (FR-026 distribution)

Per Epic, new Task sub-issues that `/speckit-taskstoissues` will link via `addSubIssue` mutation to the owning Epic (NOT to Epic M):

| Epic | New REWRITE Tasks | Cumulative headroom* |
|---|---:|---|
| H #1302 | 13 | ample (H has no prior sub-issues) |
| K #1308 | 8 | ample |
| D #1299 | 4 | ample |
| J #1307 | 4 | ample |
| E #1300 | 3 | ample |
| I #1303 | 2 | ample |
| L #1309 | 1 | ample |

\* "ample" = receiving Epic is fresh (entered Spec Kit cycle separately); no existing Tasks to displace. Each non-M Epic will run its own `/speckit-tasks` + `/speckit-taskstoissues` cycle later; Epic M's run adds these as **additional** Tasks before those cycles, which is the FR-026 contract.

## 5 · Pre-flight gate result

✅ **PASS** — 55 non-`[Deferred]` Epic-M Tasks projected ≤ 85 early-warning threshold. No aggregation escalation required.
