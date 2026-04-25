# Memdir Path Contract — Spec 1635 UI L2

This document enumerates every memdir path read or written by this epic. The USER-tier root is `~/.kosmos/memdir/user/` (owned by Spec 027). New paths are owned by this epic. Existing paths are read-only or write-through to Spec 033 / Spec 035.

## New paths (owned by this epic)

| Path | Owner | Purpose | FR | Schema |
|---|---|---|---|---|
| `~/.kosmos/memdir/user/onboarding/state.json` | Spec 1635 | Resumable 5-step onboarding state | FR-002 | `OnboardingState` (data-model.md §1) |
| `~/.kosmos/memdir/user/preferences/a11y.json` | Spec 1635 | Accessibility toggles persisted across sessions | FR-005 | `AccessibilityPreference` (data-model.md §5) |

Both files are atomic-rename writes (`fs.writeFile` to `*.tmp` then `fs.rename`), idempotent, and version-tagged with `schema_version: 1` for forward compatibility. Read failures fall through to default values; the TUI never crashes on a missing or malformed JSON.

## Existing paths (read or write-through, not owned)

| Path | Owner | This epic's interaction |
|---|---|---|
| `~/.kosmos/memdir/user/consent/` | Spec 035 + Spec 033 | Read-only — `/consent list` queries the existing ledger. Writes go via the IPC envelope to the Python permission service; the TUI never appends directly. |
| `~/.kosmos/memdir/user/sessions/` | Spec 027 | Read-only — `/history` filters across this directory by date / session-id / Layer. |
| `~/.kosmos/memdir/user/ministry-scope/` | Spec 035 | Read + write-through — onboarding step 4 (`ministry-scope`) writes the citizen's opt-in set. The TS code calls the Spec 035 helper, never `fs.writeFile` directly. |

## Out-of-scope memdir tiers

| Tier | Path root | Why excluded |
|---|---|---|
| PROJECT | `<project>/.kosmos/memdir/project/` | Citizen surface is per-OS-user; project-scoped state is irrelevant to this epic. |
| GLOBAL | `~/.kosmos/memdir/global/` | Owned by ops; UI-L2 never writes here. |

## Egress / network surface

Zero. Every read/write is local POSIX filesystem. No HTTP, no gRPC, no IPC outside the existing Spec 032 stdio envelope. SC-008 verification: `lsof -p $(pgrep -f 'bun.*tui')` during a representative session shows no new TCP connections beyond the Spec 028 OTLP collector localhost endpoint already established by previous specs.
