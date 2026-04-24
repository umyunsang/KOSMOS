# Epic P0 · Baseline Runnable

## Objective

Make `bun run src/main.tsx` execute without compile errors and render the CC `<App>` baseline on screen.

## Acceptance criteria

- [ ] `bun install` completes with 0 missing deps
- [ ] `bun run src/main.tsx` renders the CC splash for ≥3 seconds without crash
- [ ] `bun test` passes ≥ 540 tests (regression from 449 currently passing; upstream baseline is 549)
- [ ] All `bun:bundle` `feature()` calls resolve to `() => false`

## File-level scope

### `tui/package.json`

install (add to `dependencies`):
- `@commander-js/extra-typings` — CLI parser used at lines 22/976
- `chalk` — terminal colouring, line 23
- `lodash-es` — `mapValues`, `pickBy`, `uniqBy` used at lines 25–27; tsconfig already stubs `lodash-es/*` to `any-stub`, so runtime stub suffices
- `chokidar` — direct package import from `src/keybindings/loadUserBindings.ts` (causes 17 errors in current test run)
- `@anthropic-ai/sdk` — tsconfig stubs the type path but the package itself is absent at runtime; `src/utils/errors.ts` and `src/hooks/useCanUseTool.tsx` resolve it at runtime

### `tui/src/main.tsx`

strip (Anthropic-only bootstrap, safe to no-op for P0):
- Lines 9–20: `profileCheckpoint`, `startMdmRawRead()`, `startKeychainPrefetch()` — MDM/keychain prefetch side-effects
- Lines 13–17 imports: `./utils/startupProfiler`, `./utils/settings/mdm/rawRead`, `./utils/secureStorage/keychainPrefetch`
- Lines 32, 36: `initializeTelemetryAfterTrust`, `initializeGrowthBook` / `refreshGrowthBookAfterAuthChange`
- Lines 29, 83–86: `getOauthConfig`, `src/services/analytics/*` (4 imports)

stub (`bun:bundle` feature flags — 61 call-sites, 17 distinct flags):
- `feature()` → `() => false` covering: `COORDINATOR_MODE`, `KAIROS`, `KAIROS_BRIEF`, `KAIROS_CHANNELS`, `TRANSCRIPT_CLASSIFIER`, `DIRECT_CONNECT`, `LODESTONE`, `SSH_REMOTE`, `UDS_INBOX`, `BG_SESSIONS`, `UPLOAD_USER_SETTINGS`, `WEB_BROWSER_TOOL`, `CHICAGO_MCP`, `PROACTIVE`, `HARD_FAIL`, `CCR_MIRROR`, `AGENT_MEMORY_SNAPSHOT`, `BRIDGE_MODE`

### `tui/tsconfig.json`

paths additions needed:
- `src/*` → `["./src/*"]` — CC uses bare `src/` imports (e.g. `src/services/analytics/config.js`) but no `src/*` path entry exists; only `@/*` is mapped

### Directory structure fix

The `cp` doubled one nesting level: `src/constants/constants/`, `src/services/services/`. Files in `constants/constants/oauth.ts` and `services/services/api/dumpPrompts.ts` must be reachable as `constants/oauth` and `services/api/dumpPrompts`. Either move files up one level or add tsconfig path remaps.

### Stub modules to create under `tui/src/stubs/`

- `bun-bundle.ts` — `export const feature = (_: string) => false`
- (existing `any-stub.ts` already covers `lodash-es/*`, `@alcalzone/ansi-tokenize`, `semver`, `usehooks-ts`, `@anthropic-ai/sdk/*` for type resolution)

## Out of scope (deferred to P1+)

Anthropic API replacement · OAuth / MDM / keychain real flows · GrowthBook analytics · MCP claude.ai connectors · telemetry sinks · coordinator/KAIROS/SSH feature branches

## Dependencies

None (P0 is the bottom of the DAG).

## Related decisions

`docs/requirements/kosmos-migration-tree.md § P0`
