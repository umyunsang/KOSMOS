# ADR-009: Drop CC `utils/secureStorage/` — `.env` as Sole Credential Surface

**Status**: Accepted
**Date**: 2026-05-03
**Epic**: #2643 (Epic G — Utils 잔존 정리, Initiative #2636 CC Migration Audit)
**Affected**: `tui/src/utils/` (deletion of CC subtree, no replacement)

## Context

Audit Initiative #2636 (`specs/cc-migration-audit/scope-S9-utils.md § P0-2~6 + § 사용자 결정 필요 D2`) flagged that the CC source-of-truth at `.references/claude-code-sourcemap/restored-src/src/utils/secureStorage/` ships **6 files / 629 LOC** of credential storage infrastructure that UMMAYA does not implement:

| CC file | LOC | Role |
|---|---:|---|
| `index.ts` | 17 | Platform dispatcher (macOS Keychain + fallback) |
| `macOsKeychainStorage.ts` | 231 | macOS Keychain CLI wrapper |
| `keychainPrefetch.ts` | 116 | Eager-load cache for Keychain entries |
| `macOsKeychainHelpers.ts` | 111 | macOS-specific helper utilities |
| `fallbackStorage.ts` | 70 | Composite storage with fallback chain |
| `plainTextStorage.ts` | 84 | Plain-text JSON file storage (Linux fallback) |
| **Total** | **629** | — |

CC uses these 6 files to encrypt OAuth refresh tokens, API keys, and `claude.ai` subscription tokens at rest, with macOS Keychain as the primary store and a plaintext fallback for Linux.

UMMAYA has none of these surfaces:
- **No OAuth flow**: UMMAYA = single FriendliAI API key (Spec 1633 dead-code purge removed all Anthropic / `claude.ai` OAuth + subscriber surfaces).
- **No multi-tenant credential pool**: UMMAYA Phase P3 currently uses one `data.go.kr` API key (the umbrella key for KOROAD / KMA / HIRA / NMC adapters) plus one FriendliAI token — both sourced from `.env`.
- **No macOS-specific credential semantics**: UMMAYA targets cross-platform (macOS dev, Linux CI/prod) with the same `.env` discipline.

The audit decision (`specs/cc-migration-audit/decisions.md § S9 Utils` row 2) accepted **DROP**: do not port the 6 CC files; preserve `.env`-only credential surface.

## Decision

UMMAYA **drops** the entire `utils/secureStorage/` subtree from the CC byte-copy port. The `.env` file (loaded via existing `pydantic-settings` `BaseSettings` infrastructure on the Python side, and via `process.env` on the TUI side) is the sole credential surface for the foreseeable future.

**UMMAYA-side affected paths**:
- `tui/src/utils/secureStorage/` — directory does NOT exist (intentional).
- No callsite in UMMAYA imports from this path. Verification: `grep -rn "secureStorage" tui/src/` returns 0 matches.

**Implications**:
- UMMAYA auth = `UMMAYA_FRIENDLI_TOKEN` + `UMMAYA_DATA_GO_KR_KEY` env vars only.
- No persisted credentials on disk outside `.env` (which is `.gitignore`'d per AGENTS.md hard rule).
- No platform-specific credential code paths. Linux/macOS behave identically.

## Consequences

**Positive**:
- **Smaller attack surface**: 0 credential files on disk vs CC's 6. No keychain CLI subprocess invocations. No plaintext fallback file at risk of accidental commit.
- **Simpler deployment**: Docker container + devcontainer just need `.env` mounted; no platform-specific credential bootstrap.
- **No new dependencies**: AGENTS.md hard rule "Never add a dependency outside a spec-driven PR" preserved trivially (CC's `secureStorage/` would have required `keytar`-equivalent native binaries).
- **CORE THESIS preservation**: UMMAYA = CC + 2 swaps. The DROP is justified because CC's credential surface (Anthropic OAuth + claude.ai subscription) is one of the explicit "everything else" categories that the swap-2 (Korean public API tools) does not need.

**Negative / Limitations**:
- **No multi-tenant key isolation**: If UMMAYA ever needs to manage per-citizen API keys (e.g., a citizen's individual 정부24 OAuth token rather than the institutional API key), `.env` alone is insufficient. Future trigger covers this.
- **No credential rotation tooling**: PIPA-class C2 keys (which mandate periodic rotation) cannot be rotated without manual `.env` edit + restart. Future trigger covers this.
- **No OS-level credential UI**: Users who expect macOS Keychain prompts for new keys see a `.env`-edit workflow instead. Acceptable for current developer-persona admin path; reconsidered if UMMAYA gains a citizen-administered onboarding flow.

## Future Trigger

This ADR MUST be revisited (and the 6 CC files PORTed) when **any of the following measurable conditions** is met:

1. **Multi-tenant API key requirement**: UMMAYA simultaneously manages **≥ 2 distinct ministry API keys** with per-tenant isolation that `UMMAYA_*` env-prefix scoping cannot provide (e.g., keys with conflicting names, per-citizen-session credential bindings, or separate quota accounting per credential).
2. **PIPA-class C2 key rotation policy mandate**: A UMMAYA-handled credential becomes subject to PIPA-class C2 (Personal Information Protection Act, 개인정보보호법 §29 + 표준 개인정보 보호 지침) mandatory key rotation policy — typically when the key authorizes citizen PII access (예: 모바일신분증 발급 토큰, 마이데이터 access token).
3. **Citizen-administered credential UX**: UMMAYA gains a UI L2 surface where citizens enter their own credentials (e.g., 카카오 인증서 / 공동인증서 token after PASS authentication), requiring OS-level credential storage prompts.
4. **External plugin requires OS-level secret store**: A plugin manifest under `ummaya-plugin-store/` declares `requires_secure_storage: true` and the plugin DX team accepts the requirement (would itself require an ADR amendment to Spec 1636 plugin manifest schema).

When triggered, the PORT scope is the 6 CC files listed in the Context section above, byte-identical from `.references/claude-code-sourcemap/restored-src/src/utils/secureStorage/` with swap-1 deviations limited to (a) Anthropic SDK type imports replaced via `src/sdk-compat.js` shim per Spec 2521, (b) error message strings preserved English source per AGENTS.md hard rule.

## References

- `specs/cc-migration-audit/scope-S9-utils.md § P0-2~6` (audit identification)
- `specs/cc-migration-audit/decisions.md § S9 Utils` row 2 (DROP decision)
- `specs/2643-utils-residue/spec.md § US4 + FR-017 ~ FR-020` (this Epic)
- `AGENTS.md § Hard rules` (`UMMAYA_*` env prefix + never commit `.env`)
- `.specify/memory/constitution.md § II Fail-Closed Security` + § IV Government API Compliance (no hardcoded keys; all credentials via `UMMAYA_*` env vars)
