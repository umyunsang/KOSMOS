// SPDX-License-Identifier: Apache-2.0
//
// Tests for the `/plugin` slash command (Spec 1636 P5 / T053-T057).
//
// The command emits exactly one plugin_op_request frame per invocation
// (or a help-text acknowledgement for the no-op cases). We capture the
// emitted frame via a mock SendPluginOp callback and assert shape +
// payload per contracts/plugin-install.cli.md.

import { describe, expect, it, mock } from 'bun:test'
import pluginCommand from '../../src/commands/plugin'
import type {
  CommandHandlerArgs,
  SendFrame,
  SendPluginOp,
} from '../../src/commands/types'
import type {
  PluginOpFrame,
  SessionEventFrame,
} from '../../src/ipc/frames.generated'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMocks(): {
  args: (raw: string) => CommandHandlerArgs
  sessionFrames: SessionEventFrame[]
  pluginFrames: PluginOpFrame[]
} {
  const sessionFrames: SessionEventFrame[] = []
  const pluginFrames: PluginOpFrame[] = []
  const sendFrame: SendFrame = (frame) => {
    sessionFrames.push(frame)
  }
  const sendPluginOp: SendPluginOp = (frame) => {
    pluginFrames.push(frame)
  }
  return {
    args: (raw: string) => ({ args: raw, sendFrame, sendPluginOp }),
    sessionFrames,
    pluginFrames,
  }
}

function makeArgsWithoutPluginOp(raw: string): CommandHandlerArgs {
  const sendFrame: SendFrame = mock(() => undefined)
  return { args: raw, sendFrame }
}

// ---------------------------------------------------------------------------
// /plugin install
// ---------------------------------------------------------------------------

describe('/plugin install', () => {
  it('emits plugin_op_request with op=request request_op=install', () => {
    const { args, pluginFrames } = makeMocks()
    const result = pluginCommand.handle(args('install seoul-subway'))
    expect(typeof result === 'object' && 'acknowledgement' in result).toBe(true)
    expect(pluginFrames).toHaveLength(1)
    const frame = pluginFrames[0]!
    expect(frame.kind).toBe('plugin_op')
    expect(frame.op).toBe('request')
    expect(frame.request_op).toBe('install')
    expect(frame.name).toBe('seoul-subway')
    expect(frame.role).toBe('tui')
  })

  it('parses --version flag', () => {
    const { args, pluginFrames } = makeMocks()
    pluginCommand.handle(args('install seoul-subway --version 1.2.0'))
    expect(pluginFrames).toHaveLength(1)
    const frame = pluginFrames[0]!
    expect(frame.requested_version).toBe('1.2.0')
  })

  it('parses --dry-run flag', () => {
    const { args, pluginFrames } = makeMocks()
    pluginCommand.handle(args('install seoul-subway --dry-run'))
    expect(pluginFrames).toHaveLength(1)
    const frame = pluginFrames[0]!
    expect(frame.dry_run).toBe(true)
  })

  it('returns help text when name is missing', () => {
    const { args, pluginFrames } = makeMocks()
    const result = pluginCommand.handle(args('install'))
    expect(pluginFrames).toHaveLength(0)
    if (typeof result === 'object' && 'acknowledgement' in result) {
      expect(result.acknowledgement).toContain('이름이 필요합니다')
    } else {
      throw new Error('expected sync result')
    }
  })

  it('returns IPC-disconnected error when sendPluginOp is missing', () => {
    const result = pluginCommand.handle(makeArgsWithoutPluginOp('install seoul-subway'))
    if (typeof result === 'object' && 'acknowledgement' in result) {
      expect(result.acknowledgement).toContain('IPC 가 연결되지 않았습니다')
    } else {
      throw new Error('expected sync result')
    }
  })
})

// ---------------------------------------------------------------------------
// /plugin list
// ---------------------------------------------------------------------------

describe('/plugin list', () => {
  it('emits plugin_op_request with request_op=list', () => {
    const { args, pluginFrames } = makeMocks()
    pluginCommand.handle(args('list'))
    expect(pluginFrames).toHaveLength(1)
    const frame = pluginFrames[0]!
    expect(frame.request_op).toBe('list')
    expect(frame.name).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// /plugin uninstall
// ---------------------------------------------------------------------------

describe('/plugin uninstall', () => {
  it('emits plugin_op_request with request_op=uninstall', () => {
    const { args, pluginFrames } = makeMocks()
    pluginCommand.handle(args('uninstall seoul-subway'))
    expect(pluginFrames).toHaveLength(1)
    const frame = pluginFrames[0]!
    expect(frame.request_op).toBe('uninstall')
    expect(frame.name).toBe('seoul-subway')
  })

  it('returns help text when name is missing', () => {
    const { args, pluginFrames } = makeMocks()
    const result = pluginCommand.handle(args('uninstall'))
    expect(pluginFrames).toHaveLength(0)
    if (typeof result === 'object' && 'acknowledgement' in result) {
      expect(result.acknowledgement).toContain('이름이 필요합니다')
    } else {
      throw new Error('expected sync result')
    }
  })
})

// ---------------------------------------------------------------------------
// /plugin pipa-text
// ---------------------------------------------------------------------------

describe('/plugin pipa-text', () => {
  it('returns canonical hash without IPC traffic', () => {
    const { args, pluginFrames } = makeMocks()
    const result = pluginCommand.handle(args('pipa-text'))
    expect(pluginFrames).toHaveLength(0)
    if (typeof result === 'object' && 'acknowledgement' in result) {
      expect(result.acknowledgement).toContain(
        '434074581cab35241c70f9b6e2191a7220fdac67aa627289ea64472cb87495d4',
      )
      expect(result.acknowledgement).toContain('docs/plugins/security-review.md')
    } else {
      throw new Error('expected sync result')
    }
  })
})

// ---------------------------------------------------------------------------
// Unknown / empty subcommand
// ---------------------------------------------------------------------------

describe('/plugin unknown / empty', () => {
  it('shows usage when no subcommand', () => {
    const { args, pluginFrames } = makeMocks()
    const result = pluginCommand.handle(args(''))
    expect(pluginFrames).toHaveLength(0)
    if (typeof result === 'object' && 'acknowledgement' in result) {
      expect(result.acknowledgement).toContain('사용법')
    } else {
      throw new Error('expected sync result')
    }
  })

  it('shows error + usage for unknown subcommand', () => {
    const { args, pluginFrames } = makeMocks()
    const result = pluginCommand.handle(args('reinstall foo'))
    expect(pluginFrames).toHaveLength(0)
    if (typeof result === 'object' && 'acknowledgement' in result) {
      expect(result.acknowledgement).toContain('알 수 없는 subcommand')
      expect(result.acknowledgement).toContain('reinstall')
    } else {
      throw new Error('expected sync result')
    }
  })
})

// ---------------------------------------------------------------------------
// Frame envelope shape
// ---------------------------------------------------------------------------

describe('plugin_op frame envelope', () => {
  it('every emitted frame carries kind / version / role / op', () => {
    const { args, pluginFrames } = makeMocks()
    pluginCommand.handle(args('install seoul-subway'))
    pluginCommand.handle(args('list'))
    pluginCommand.handle(args('uninstall seoul-subway'))
    expect(pluginFrames).toHaveLength(3)
    for (const f of pluginFrames) {
      expect(f.kind).toBe('plugin_op')
      expect(f.version).toBe('1.0')
      expect(f.role).toBe('tui')
      expect(f.op).toBe('request')
      expect(typeof f.correlation_id).toBe('string')
      expect(f.correlation_id.length).toBeGreaterThan(0)
    }
  })

  it('does not bleed into the session-event channel', () => {
    const { args, pluginFrames, sessionFrames } = makeMocks()
    pluginCommand.handle(args('install seoul-subway'))
    expect(pluginFrames).toHaveLength(1)
    expect(sessionFrames).toHaveLength(0)
  })
})
