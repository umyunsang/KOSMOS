// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/defaultBindings.ts (CC 2.1.88, research-use)
// Spec 288 · narrowed to the seven Tier 1 actions per data-model.md § 2.
//
// This file is the seed of `KeybindingRegistry` (T012). The merge with
// `loadUserBindings()` output yields the runtime registry; no
// `effective_chord` divergence is allowed in this seed.

import { parseChord } from './chord'
import {
  type KeybindingEntry,
  type TierOneAction,
  type ChordString,
} from './types'

// ---------------------------------------------------------------------------
// Platform-specific shift+tab fallback (D3, ports CC L17-L30).
// ---------------------------------------------------------------------------

function isWindows(): boolean {
  return typeof process !== 'undefined' && process.platform === 'win32'
}

function bunSupportsVT(): boolean {
  const bunVer = (process.versions as { bun?: string } | undefined)?.bun
  if (bunVer === undefined) return true // Node-side or non-Bun runtime
  // Compare semver triple naively; full satisfies() lives in Lead's port.
  const m = /^(\d+)\.(\d+)\.(\d+)/.exec(bunVer)
  if (m === null) return true
  const major = Number(m[1] ?? '0')
  const minor = Number(m[2] ?? '0')
  const patch = Number(m[3] ?? '0')
  if (major > 1) return true
  if (major < 1) return false
  if (minor > 2) return true
  if (minor < 2) return false
  return patch >= 23
}

const SUPPORTS_TERMINAL_VT_MODE = !isWindows() || bunSupportsVT()
export const MODE_CYCLE_DEFAULT_CHORD = SUPPORTS_TERMINAL_VT_MODE
  ? 'shift+tab'
  : 'meta+m'

// ---------------------------------------------------------------------------
// Tier 1 default bindings (data-model.md § 2)
// ---------------------------------------------------------------------------

type SeedSpec = {
  action: TierOneAction
  default_chord: string
  context: KeybindingEntry['context']
  description: string
  remappable: boolean
  reserved: boolean
  mutates_buffer: boolean
}

const SEED: readonly SeedSpec[] = [
  {
    action: 'agent-interrupt',
    default_chord: 'ctrl+c',
    context: 'Global',
    description:
      '에이전트 루프 즉시 중단 / Interrupt the active agent loop immediately',
    remappable: false,
    reserved: true,
    mutates_buffer: false,
  },
  {
    action: 'session-exit',
    default_chord: 'ctrl+d',
    context: 'Global',
    description:
      '세션 정리 후 안전 종료 / Flush audit and exit cleanly',
    remappable: false,
    reserved: true,
    mutates_buffer: false,
  },
  {
    action: 'draft-cancel',
    default_chord: 'escape',
    context: 'Chat',
    description:
      '입력창 초안 비우기 (한글 조합 중에는 무시) / Clear draft (no-op while IME composes)',
    remappable: true,
    reserved: false,
    mutates_buffer: true,
  },
  {
    action: 'history-search',
    default_chord: 'ctrl+r',
    context: 'Global',
    description:
      '이전 질문 검색 오버레이 열기 / Open history-search overlay',
    remappable: true,
    reserved: false,
    mutates_buffer: false,
  },
  {
    action: 'history-prev',
    default_chord: 'up',
    context: 'Chat',
    description:
      '직전 질문 불러오기 (빈 입력창에서만) / Load previous query (empty buffer only)',
    remappable: true,
    reserved: false,
    mutates_buffer: true,
  },
  {
    action: 'history-next',
    default_chord: 'down',
    context: 'Chat',
    description:
      '다음 질문 불러오기 (빈 입력창에서만) / Load next query (empty buffer only)',
    remappable: true,
    reserved: false,
    mutates_buffer: true,
  },
  {
    action: 'permission-mode-cycle',
    default_chord: MODE_CYCLE_DEFAULT_CHORD,
    context: 'Global',
    description:
      '권한 모드 순환 (plan→default→acceptEdits→bypassPermissions) / Cycle PermissionMode',
    remappable: true,
    reserved: false,
    mutates_buffer: false,
  },
] as const

function buildEntry(spec: SeedSpec): KeybindingEntry {
  const chord: ChordString = parseChord(spec.default_chord)
  return Object.freeze({
    action: spec.action,
    default_chord: chord,
    effective_chord: chord,
    context: spec.context,
    description: spec.description,
    remappable: spec.remappable,
    reserved: spec.reserved,
    mutates_buffer: spec.mutates_buffer,
  })
}

export const DEFAULT_BINDINGS: ReadonlyArray<KeybindingEntry> = Object.freeze(
  SEED.map(buildEntry),
)

export function defaultBindingsByAction(): ReadonlyMap<
  TierOneAction,
  KeybindingEntry
> {
  const m = new Map<TierOneAction, KeybindingEntry>()
  for (const e of DEFAULT_BINDINGS) m.set(e.action, e)
  return m
}
