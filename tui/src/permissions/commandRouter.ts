// SPDX-License-Identifier: Apache-2.0
// Spec 033 T043 — Slash-command routing for /permissions sub-commands.
//
// Handles:
//   /permissions bypass    — activate bypassPermissions (after dialog)
//   /permissions dontAsk   — activate dontAsk (after dialog)
//   /permissions default   — reset to default from any mode
//   /permissions list      — list current rules
//   /permissions edit      — edit a rule for a specific adapter
//   /permissions verify    — verify consent ledger chain integrity
//
// This module integrates with the existing CommandDefinition / CommandRegistry
// pattern from tui/src/commands/dispatcher.ts.
//
// OTEL emission for mode changes happens via emitModeChangedOtel (T046).

import type { CommandDefinition, CommandHandlerArgs, CommandResult } from '../commands/types'
import type { PermissionMode, PermissionRule } from './types'
import { emitModeChangedOtel } from './otelEmit'

// ---------------------------------------------------------------------------
// Callback interface injected at wiring time
// ---------------------------------------------------------------------------

/**
 * Callbacks injected by the TUI wiring layer.
 * This allows the command router to mutate TUI state without importing stores.
 */
export interface PermissionCommandCallbacks {
  /** Get current mode */
  getMode: () => PermissionMode
  /** Trigger bypass confirmation dialog and await result */
  requestBypassConfirm: () => Promise<boolean>
  /** Trigger dontAsk confirmation dialog and await result */
  requestDontAskConfirm: () => Promise<boolean>
  /** Update the current mode */
  setMode: (mode: PermissionMode) => void
  /** Get the current list of rules */
  getRules: () => PermissionRule[]
  /** Session ID for OTEL envelopes */
  getSessionId: () => string
}

// ---------------------------------------------------------------------------
// Sub-command handler factory
// ---------------------------------------------------------------------------

/**
 * Build CommandDefinition objects for each /permissions sub-command.
 *
 * Usage in the registry builder:
 *   const cmds = buildPermissionCommands(callbacks)
 *   cmds.forEach(cmd => registerCommand(registry, cmd))
 */
export function buildPermissionCommands(
  callbacks: PermissionCommandCallbacks,
): CommandDefinition[] {
  return [
    _bypassCommand(callbacks),
    _dontAskCommand(callbacks),
    _defaultCommand(callbacks),
    _listCommand(callbacks),
    _editCommand(),
    _verifyCommand(callbacks),
  ]
}

// ---------------------------------------------------------------------------
// Individual command definitions
// ---------------------------------------------------------------------------

function _bypassCommand(cb: PermissionCommandCallbacks): CommandDefinition {
  return {
    name: 'permissions bypass',
    description: 'Activate bypassPermissions mode (requires confirmation)',
    handle: async (_args: CommandHandlerArgs): Promise<CommandResult> => {
      const fromMode = cb.getMode()
      if (fromMode === 'bypassPermissions') {
        return { acknowledgement: '이미 우회(bypassPermissions) 모드입니다.' }
      }
      const confirmed = await cb.requestBypassConfirm()
      if (!confirmed) {
        return { acknowledgement: '우회 모드 전환이 취소되었습니다.' }
      }
      cb.setMode('bypassPermissions')
      emitModeChangedOtel({
        fromMode,
        toMode: 'bypassPermissions',
        trigger: 'slash_command',
        confirmed: true,
        sessionId: cb.getSessionId(),
      })
      return { acknowledgement: '⚠ 우회(bypassPermissions) 모드가 활성화되었습니다. 상태바를 확인하세요.' }
    },
  }
}

function _dontAskCommand(cb: PermissionCommandCallbacks): CommandDefinition {
  return {
    name: 'permissions dontAsk',
    description: 'Activate dontAsk mode (requires confirmation)',
    handle: async (_args: CommandHandlerArgs): Promise<CommandResult> => {
      const fromMode = cb.getMode()
      if (fromMode === 'dontAsk') {
        return { acknowledgement: '이미 사전허용(dontAsk) 모드입니다.' }
      }
      const confirmed = await cb.requestDontAskConfirm()
      if (!confirmed) {
        return { acknowledgement: '사전허용 모드 전환이 취소되었습니다.' }
      }
      cb.setMode('dontAsk')
      emitModeChangedOtel({
        fromMode,
        toMode: 'dontAsk',
        trigger: 'slash_command',
        confirmed: true,
        sessionId: cb.getSessionId(),
      })
      return { acknowledgement: '사전허용(dontAsk) 모드가 활성화되었습니다.' }
    },
  }
}

function _defaultCommand(cb: PermissionCommandCallbacks): CommandDefinition {
  return {
    name: 'permissions default',
    description: 'Reset permission mode to default',
    handle: (_args: CommandHandlerArgs): CommandResult => {
      const fromMode = cb.getMode()
      if (fromMode === 'default') {
        return { acknowledgement: '이미 기본(default) 모드입니다.' }
      }
      cb.setMode('default')
      emitModeChangedOtel({
        fromMode,
        toMode: 'default',
        trigger: 'slash_command',
        confirmed: true,
        sessionId: cb.getSessionId(),
      })
      return { acknowledgement: '기본(default) 모드로 초기화되었습니다.' }
    },
  }
}

function _listCommand(cb: PermissionCommandCallbacks): CommandDefinition {
  return {
    name: 'permissions list',
    description: 'List current permission rules',
    handle: (_args: CommandHandlerArgs): CommandResult => {
      const rules = cb.getRules()
      if (rules.length === 0) {
        return {
          acknowledgement: '저장된 규칙이 없습니다.',
          renderHelp: false,
        }
      }
      // The TUI layer renders RuleListView when it sees 'render_rule_list' hint.
      // We return the rules serialized in acknowledgement for non-visual handlers.
      const lines = rules.map(
        (r) => `  ${r.tool_id} | ${r.scope} | ${r.decision} | ${r.created_at}`,
      )
      return {
        acknowledgement: `권한 규칙 (${rules.length}개):\n${lines.join('\n')}`,
      }
    },
  }
}

function _editCommand(): CommandDefinition {
  return {
    name: 'permissions edit',
    description: 'Edit permission rule for a specific adapter',
    argumentHint: '<tool_id> [allow|ask|deny]',
    handle: (args: CommandHandlerArgs): CommandResult => {
      const parts = args.args.split(/\s+/)
      const toolId = parts[0]
      const decision = parts[1]

      if (!toolId) {
        return {
          acknowledgement:
            '사용법: /permissions edit <tool_id> [allow|ask|deny]\n예: /permissions edit kma_forecast_fetch allow',
        }
      }

      const validDecisions = new Set(['allow', 'ask', 'deny'])
      if (decision && !validDecisions.has(decision)) {
        return {
          acknowledgement: `유효하지 않은 결정값: "${decision}". allow | ask | deny 중 하나를 선택하세요.`,
        }
      }

      // Full persistence is handled by the Python backend; TUI sends an IPC event.
      // For now, return an acknowledgement — backend wiring is Lead's responsibility.
      return {
        acknowledgement: decision
          ? `규칙 변경 요청: ${toolId} → ${decision} (백엔드 연동 대기 중)`
          : `규칙 조회 요청: ${toolId} (백엔드 연동 대기 중)`,
      }
    },
  }
}

function _verifyCommand(cb: PermissionCommandCallbacks): CommandDefinition {
  return {
    name: 'permissions verify',
    description: 'Verify consent ledger chain integrity',
    handle: (_args: CommandHandlerArgs): CommandResult => {
      // Ledger verification runs in the Python backend via the
      // `kosmos-permissions verify` CLI.  IPC dispatch is not yet wired from
      // the TUI — Lead integration will add a session_event trigger.
      // Until then the acknowledgement must not claim a request was sent.
      void cb.getSessionId() // reference to avoid unused-variable lint
      return {
        acknowledgement:
          '동의 원장 검증은 아직 TUI에서 실행되지 않습니다. ' +
          "터미널에서 'kosmos-permissions verify' 명령으로 수동 실행하세요.",
      }
    },
  }
}

// ---------------------------------------------------------------------------
// Parse sub-command from "/permissions <sub>" input
// ---------------------------------------------------------------------------

/**
 * Extract the sub-command name from raw input like "/permissions bypass".
 * Returns null if the input does not start with "/permissions ".
 */
export function parsePermissionsSubCommand(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed.startsWith('/permissions')) return null
  const rest = trimmed.slice('/permissions'.length).trim()
  return rest || null
}

/**
 * Route a "/permissions <sub>" input string to the matching CommandDefinition.
 * Returns null if not a /permissions command or no matching sub-command.
 */
export function routePermissionsCommand(
  input: string,
  commands: CommandDefinition[],
): CommandDefinition | null {
  const trimmed = input.trim()
  if (!trimmed.startsWith('/permissions')) return null

  // Build full command name: "permissions <sub>" or "permissions" for bare /permissions
  const rest = trimmed.slice('/permissions'.length).trim()
  const fullName = rest ? `permissions ${rest.split(/\s+/)[0]}` : 'permissions'

  return commands.find((c) => c.name === fullName) ?? null
}
