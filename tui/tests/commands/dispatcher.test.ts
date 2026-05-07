// T041 — Command dispatcher tests
// Tests: parse routing (known command → handler, unknown → help renderer,
//         quoted args, empty input, slash-only).

import { describe, expect, it, mock } from 'bun:test'
import {
  dispatchCommand,
  parseSlashCommand,
  isSlashCommand,
  createRegistry,
  registerCommand,
  listCommands,
} from '../../src/commands/dispatcher'
import { buildDefaultRegistry } from '../../src/commands/index'
import type { SendFrame } from '../../src/commands/types'
import type { SessionEventFrame } from '../../src/ipc/frames.generated'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMockSendFrame(): { sendFrame: SendFrame; captured: SessionEventFrame[] } {
  const captured: SessionEventFrame[] = []
  const sendFrame: SendFrame = (frame) => {
    captured.push(frame)
  }
  return { sendFrame, captured }
}

// ---------------------------------------------------------------------------
// isSlashCommand
// ---------------------------------------------------------------------------

describe('isSlashCommand', () => {
  it('returns true for /save', () => {
    expect(isSlashCommand('/save')).toBe(true)
  })

  it('returns true for /foo bar', () => {
    expect(isSlashCommand('/foo bar')).toBe(true)
  })

  it('returns false for regular text', () => {
    expect(isSlashCommand('hello world')).toBe(false)
  })

  it('returns false for empty string', () => {
    expect(isSlashCommand('')).toBe(false)
  })

  it('returns false for leading-space slash', () => {
    // " /save" is NOT a slash command — leading whitespace is significant
    expect(isSlashCommand('  /save')).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// parseSlashCommand
// ---------------------------------------------------------------------------

describe('parseSlashCommand', () => {
  it('parses /save (no args)', () => {
    expect(parseSlashCommand('/save')).toEqual({ name: 'save', args: '' })
  })

  it('parses /resume abc123', () => {
    expect(parseSlashCommand('/resume abc123')).toEqual({ name: 'resume', args: 'abc123' })
  })

  it('parses /resume with quoted arg', () => {
    const result = parseSlashCommand('/resume "my session"')
    expect(result.name).toBe('resume')
    expect(result.args).toBe('"my session"')
  })

  it('parses /new with trailing spaces', () => {
    expect(parseSlashCommand('/new  extra')).toEqual({ name: 'new', args: 'extra' })
  })

  it('lowercases the name', () => {
    expect(parseSlashCommand('/SAVE')).toEqual({ name: 'save', args: '' })
  })

  it('handles /  (slash only, space after)', () => {
    const result = parseSlashCommand('/  ')
    expect(result.name).toBe('')
    expect(result.args).toBe('')
  })
})

// ---------------------------------------------------------------------------
// dispatchCommand — known commands
// ---------------------------------------------------------------------------

describe('dispatchCommand — /save', () => {
  it('emits session_event save frame and returns acknowledgement', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('/save', registry, sendFrame)

    expect(result.commandName).toBe('save')
    expect(result.renderHelp).not.toBe(true)
    expect(result.acknowledgement.length).toBeGreaterThan(0)
    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('save')
    expect(frame.payload).toEqual({})
  })
})

describe('dispatchCommand — /sessions', () => {
  it('emits session_event list frame', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('/sessions', registry, sendFrame)

    expect(result.commandName).toBe('sessions')
    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('list')
  })
})

describe('dispatchCommand — /resume', () => {
  it('emits session_event resume frame with session_id in payload', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('/resume abc123', registry, sendFrame)

    expect(result.commandName).toBe('resume')
    expect(result.renderHelp).not.toBe(true)
    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('resume')
    expect(frame.payload).toEqual({ id: 'abc123' })
  })

  it('returns missing-id error (no frame) when no arg', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('/resume', registry, sendFrame)

    expect(captured).toHaveLength(0)
    expect(result.acknowledgement.length).toBeGreaterThan(0)
  })

  it('also responds to /continue alias', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    await dispatchCommand('/continue session-99', registry, sendFrame)

    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.event).toBe('resume')
    expect(frame.payload).toEqual({ id: 'session-99' })
  })
})

describe('dispatchCommand — /new', () => {
  it('emits session_event new frame', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('/new', registry, sendFrame)

    expect(result.commandName).toBe('new')
    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('new')
    expect(frame.payload).toEqual({})
  })
})

// ---------------------------------------------------------------------------
// dispatchCommand — unknown command → help
// ---------------------------------------------------------------------------

describe('dispatchCommand — unknown /foo', () => {
  it('returns renderHelp:true and does not crash', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('/foo', registry, sendFrame)

    expect(result.renderHelp).toBe(true)
    expect(result.commandName).toBe('foo')
    expect(result.acknowledgement).toContain('foo')
    expect(captured).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// dispatchCommand — edge cases
// ---------------------------------------------------------------------------

describe('dispatchCommand — edge cases', () => {
  it('returns empty result for empty input (no frame)', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('', registry, sendFrame)

    expect(result.commandName).toBe('')
    expect(result.acknowledgement).toBe('')
    expect(captured).toHaveLength(0)
  })

  it('returns empty result for non-slash input', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeMockSendFrame()

    const result = await dispatchCommand('hello world', registry, sendFrame)

    expect(result.commandName).toBe('')
    expect(captured).toHaveLength(0)
  })

  it('shows help for bare /', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame } = makeMockSendFrame()

    const result = await dispatchCommand('/', registry, sendFrame)

    expect(result.renderHelp).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// registerCommand — duplicate detection
// ---------------------------------------------------------------------------

describe('registerCommand', () => {
  it('throws on duplicate name', () => {
    const registry = createRegistry()
    registerCommand(registry, {
      name: 'foo',
      description: 'Foo command',
      handle: () => ({ acknowledgement: 'ok' }),
    })
    expect(() =>
      registerCommand(registry, {
        name: 'foo',
        description: 'Foo again',
        handle: () => ({ acknowledgement: 'ok2' }),
      }),
    ).toThrow('foo')
  })

  it('throws on duplicate alias', () => {
    const registry = createRegistry()
    registerCommand(registry, {
      name: 'bar',
      description: 'Bar',
      aliases: ['b'],
      handle: () => ({ acknowledgement: 'ok' }),
    })
    expect(() =>
      registerCommand(registry, {
        name: 'baz',
        description: 'Baz',
        aliases: ['b'],
        handle: () => ({ acknowledgement: 'ok' }),
      }),
    ).toThrow('b')
  })
})

// ---------------------------------------------------------------------------
// listCommands — deduplication
// ---------------------------------------------------------------------------

describe('listCommands', () => {
  it('returns unique entries even when aliases are registered', () => {
    const registry = buildDefaultRegistry()
    const commands = listCommands(registry)

    // /resume has alias /continue — should appear once
    const resumeEntries = commands.filter((c) => c.name === 'resume')
    expect(resumeEntries).toHaveLength(1)

    // Sorted by name
    const names = commands.map((c) => c.name)
    expect(names).toEqual([...names].sort())
  })
})
