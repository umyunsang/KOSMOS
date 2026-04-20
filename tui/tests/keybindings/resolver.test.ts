// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T025 — resolver precedence + IME gate + OTel span emission
// (FR-003, FR-005, FR-007, FR-033, FR-034, SC-004 burst-input).

import { describe, expect, test } from 'bun:test'
import { buildChordEvent } from '../../src/keybindings/match'
import { buildRegistry } from '../../src/keybindings/registry'
import {
  drainBindingSpans,
  resolve,
  type SpanEmitter,
  type BindingSpanAttributes,
} from '../../src/keybindings/resolver'
import { loadUserBindings } from '../../src/keybindings/loadUserBindings'
import { type ChordEvent } from '../../src/keybindings/types'

function captureSpans(): {
  emitter: SpanEmitter
  taken: () => ReadonlyArray<BindingSpanAttributes>
} {
  const buf: BindingSpanAttributes[] = []
  return {
    emitter: {
      emitBinding(attrs) {
        buf.push(attrs)
      },
    },
    taken: () => Object.freeze(buf.slice()),
  }
}

function loader() {
  return loadUserBindings({ readFile: () => null })
}

describe('resolver — precedence (D7)', () => {
  test('Confirmation beats Chat beats Global', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('', {
      ctrl: false,
      shift: false,
      meta: false,
      escape: true,
    })!
    const { emitter, taken } = captureSpans()

    // Confirmation: draft-cancel lives in Chat, not Confirmation — so escape
    // in Confirmation yields no-match here (the modal wires its own handler).
    // But in Chat+Global, escape resolves to draft-cancel.
    const chatResult = resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
      spans: emitter,
    })
    expect(chatResult.kind).toBe('dispatched')
    if (chatResult.kind !== 'dispatched') throw new Error('unreachable')
    expect(chatResult.action).toBe('draft-cancel')
    expect(chatResult.context).toBe('Chat')
    const spans = taken()
    expect(spans.length).toBe(1)
    expect(spans[0]!['kosmos.tui.binding']).toBe('draft-cancel')
    expect(spans[0]!['kosmos.tui.binding.context']).toBe('Chat')
    expect(spans[0]!['kosmos.tui.binding.reserved']).toBe(false)
  })

  test('Global reserved chord resolves from Chat context (FR-016)', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('\x03', {
      ctrl: false,
      shift: false,
      meta: false,
    })!
    const result = resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
    })
    expect(result.kind).toBe('dispatched')
    if (result.kind !== 'dispatched') throw new Error('unreachable')
    expect(result.action).toBe('agent-interrupt')
  })

  test('no-match when chord unknown', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('z', {
      ctrl: false,
      shift: false,
      meta: false,
    })!
    const result = resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
    })
    expect(result.kind).toBe('no-match')
  })
})

describe('resolver — IME gate (FR-005, FR-006, FR-007)', () => {
  test('mutates_buffer action blocked while composing', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('', {
      ctrl: false,
      shift: false,
      meta: false,
      escape: true,
    })!
    const { emitter, taken } = captureSpans()
    const result = resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: true },
      spans: emitter,
    })
    expect(result.kind).toBe('blocked')
    if (result.kind !== 'blocked') throw new Error('unreachable')
    expect(result.reason).toBe('ime-composing')
    expect(result.action).toBe('draft-cancel')
    const spans = taken()
    expect(spans[0]!['kosmos.tui.binding.blocked.reason']).toBe('ime-composing')
  })

  test('non-mutating action still fires while composing', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    // ctrl+r (history-search) does NOT mutate_buffer → must pass IME gate.
    const ev = buildChordEvent('r', {
      ctrl: true,
      shift: false,
      meta: false,
    })!
    const result = resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: true },
    })
    expect(result.kind).toBe('dispatched')
    if (result.kind !== 'dispatched') throw new Error('unreachable')
    expect(result.action).toBe('history-search')
  })
})

describe('resolver — OTel span emission (FR-033 / FR-034)', () => {
  test('dispatched result emits binding + reserved + context attrs', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('\x03', {
      ctrl: false,
      shift: false,
      meta: false,
    })!
    const { emitter, taken } = captureSpans()
    resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
      spans: emitter,
    })
    const spans = taken()
    expect(spans.length).toBe(1)
    expect(spans[0]!['kosmos.tui.binding']).toBe('agent-interrupt')
    expect(spans[0]!['kosmos.tui.binding.reserved']).toBe(true)
    expect(spans[0]!['kosmos.tui.binding.chord']).toBe('ctrl+c')
  })

  test('reserved action dispatches emit audit record', async () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('\x03', {
      ctrl: false,
      shift: false,
      meta: false,
    })!
    const auditCalls: unknown[] = []
    const audit = {
      writeReservedAction: async (payload: unknown) => {
        auditCalls.push(payload)
      },
    }
    resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
      sessionId: 'sess-1',
      audit,
    })
    // Microtask flush.
    await Promise.resolve()
    expect(auditCalls.length).toBe(1)
    expect(auditCalls[0]).toMatchObject({
      event_type: 'user-interrupted',
      session_id: 'sess-1',
    })
  })

  test('audit failure does NOT abort the dispatch (FR-013 robustness)', async () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('\x04', {
      ctrl: false,
      shift: false,
      meta: false,
    })!
    const audit = {
      writeReservedAction: async () => {
        throw new Error('simulated audit failure')
      },
    }
    const result = resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
      sessionId: 'sess-1',
      audit,
    })
    expect(result.kind).toBe('dispatched')
    // Allow microtask to run and swallow the error.
    await Promise.resolve()
  })
})

describe('resolver — burst-input stability (SC-004)', () => {
  test('10 chords per 100 ms all dispatch with zero drop', () => {
    const registry = buildRegistry({ loaderResult: loader() })
    const { emitter, taken } = captureSpans()
    let t = 0
    for (let i = 0; i < 10; i += 1) {
      const ev: ChordEvent = buildChordEvent('\x03', {
        ctrl: false,
        shift: false,
        meta: false,
      }, () => (t += 10))!
      resolve(ev, {
        active: ['Chat', 'Global'],
        registry,
        ime: { isComposing: false },
        spans: emitter,
      })
    }
    expect(taken().length).toBe(10)
    expect(t).toBe(100) // 10 events × 10 ms = 100 ms
  })
})

describe('resolver — in-memory span ring drain', () => {
  test('drainBindingSpans empties after drain', () => {
    // Clear any residue from earlier tests that used the default ring.
    drainBindingSpans()
    const registry = buildRegistry({ loaderResult: loader() })
    const ev = buildChordEvent('r', {
      ctrl: true,
      shift: false,
      meta: false,
    })!
    resolve(ev, {
      active: ['Chat', 'Global'],
      registry,
      ime: { isComposing: false },
    })
    const first = drainBindingSpans()
    expect(first.length).toBe(1)
    const second = drainBindingSpans()
    expect(second.length).toBe(0)
  })
})
