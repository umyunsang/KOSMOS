// SPDX-License-Identifier: Apache-2.0
//
// `/plugin <subcommand>` slash command.
//
// Subcommands per migration tree § B8 + contracts/plugin-install.cli.md:
//   /plugin install <name> [--version v]
//   /plugin list
//   /plugin uninstall <name>
//   /plugin pipa-text                 — print canonical PIPA §26 text + hash
//
// Each subcommand emits exactly ONE plugin_op_request frame via the
// dependency-injected sendPluginOp callback. The backend installer
// (src/kosmos/plugins/installer.py) is what would consume those frames
// and reply with plugin_op_progress (phase 1-7) + plugin_op_complete.
//
// H7 (review eval): the backend stdio dispatcher that routes incoming
// plugin_op_request frames to install_plugin() is NOT wired in this
// epic — install_plugin() is fully implemented (8-phase, 6 integration
// tests + 4 SC tests), but the IPC bridge that turns a TUI request into
// a Python install_plugin() call is deferred to a follow-up. Until that
// lands, the slash command's acknowledgement carries an explicit
// "(backend not yet wired — use `kosmos plugin install` shell entry-
// point instead)" suffix so citizens are not surprised when the
// progress overlay never advances.

import type {
  CommandDefinition,
  CommandHandlerArgs,
  CommandResult,
} from './types'
// PIPA canonical hash is the Python source-of-truth (extracted from
// docs/plugins/security-review.md). The .generated.ts file is rebuilt
// by `bun run scripts/gen-pipa-hash.ts` so a TS-side drift cannot
// silently linger after the legal team rotates the canonical text.
import { CANONICAL_PIPA_ACK_SHA256 } from '../ipc/pipa.generated'

const _USAGE_KO =
  '사용법: /plugin <install|list|uninstall|pipa-text> [...]'
const _PIPA_HASH = CANONICAL_PIPA_ACK_SHA256

function _newCorrelationId(): string {
  // Use crypto.randomUUID — UUIDv4 is acceptable here since the host
  // re-stamps with UUIDv7 at the bridge boundary (Spec 032 envelope).
  return crypto.randomUUID()
}

function _now(): string {
  return new Date().toISOString()
}

function _parseSubcommand(raw: string): { sub: string; rest: string } {
  const trimmed = raw.trim()
  if (trimmed.length === 0) return { sub: '', rest: '' }
  const space = trimmed.indexOf(' ')
  if (space === -1) return { sub: trimmed, rest: '' }
  return { sub: trimmed.slice(0, space), rest: trimmed.slice(space + 1).trim() }
}

function _parseInstallArgs(rest: string): {
  name: string | undefined
  version: string | undefined
  dryRun: boolean
} {
  const tokens = rest.split(/\s+/).filter((t) => t.length > 0)
  let name: string | undefined
  let version: string | undefined
  let dryRun = false
  for (let i = 0; i < tokens.length; i += 1) {
    const tok = tokens[i]
    if (!tok) continue
    if (tok === '--version') {
      version = tokens[i + 1]
      i += 1
    } else if (tok === '--dry-run') {
      dryRun = true
    } else if (!name && !tok.startsWith('--')) {
      name = tok
    }
  }
  return { name, version, dryRun }
}

function _handleInstall(rest: string, args: CommandHandlerArgs): CommandResult {
  const { name, version, dryRun } = _parseInstallArgs(rest)
  if (!name) {
    return {
      acknowledgement: '플러그인 이름이 필요합니다: /plugin install <name>',
    }
  }
  if (!args.sendPluginOp) {
    return {
      acknowledgement: '플러그인 IPC 가 연결되지 않았습니다.',
    }
  }
  args.sendPluginOp({
    kind: 'plugin_op',
    version: '1.0',
    session_id: '',
    correlation_id: _newCorrelationId(),
    ts: _now(),
    role: 'tui',
    op: 'request',
    request_op: 'install',
    name,
    requested_version: version ?? null,
    dry_run: dryRun,
  } as never)
  const dryNote = dryRun ? ' (dry-run)' : ''
  return {
    acknowledgement: `🔄 ${name} 플러그인 설치 시작...${dryNote}`,
  }
}

function _handleList(args: CommandHandlerArgs): CommandResult {
  if (!args.sendPluginOp) {
    return {
      acknowledgement: '플러그인 IPC 가 연결되지 않았습니다.',
    }
  }
  args.sendPluginOp({
    kind: 'plugin_op',
    version: '1.0',
    session_id: '',
    correlation_id: _newCorrelationId(),
    ts: _now(),
    role: 'tui',
    op: 'request',
    request_op: 'list',
  } as never)
  return {
    acknowledgement: '📋 설치된 플러그인 목록 조회 중...',
  }
}

function _handleUninstall(rest: string, args: CommandHandlerArgs): CommandResult {
  const name = rest.trim().split(/\s+/)[0]
  if (!name) {
    return {
      acknowledgement: '플러그인 이름이 필요합니다: /plugin uninstall <name>',
    }
  }
  if (!args.sendPluginOp) {
    return {
      acknowledgement: '플러그인 IPC 가 연결되지 않았습니다.',
    }
  }
  args.sendPluginOp({
    kind: 'plugin_op',
    version: '1.0',
    session_id: '',
    correlation_id: _newCorrelationId(),
    ts: _now(),
    role: 'tui',
    op: 'request',
    request_op: 'uninstall',
    name,
  } as never)
  return {
    acknowledgement: `🗑️ ${name} 플러그인 제거 시작...`,
  }
}

function _handlePipaText(): CommandResult {
  // No IPC needed — purely informational.
  return {
    acknowledgement: [
      'PIPA §26 trustee acknowledgment canonical SHA-256:',
      `  ${_PIPA_HASH}`,
      'Source: docs/plugins/security-review.md (마커 사이 텍스트)',
      'manifest.yaml 의 acknowledgment_sha256 필드에 위 값을 그대로 기록하세요.',
    ].join('\n'),
  }
}

function handle(args: CommandHandlerArgs): CommandResult {
  const { sub, rest } = _parseSubcommand(args.args)
  switch (sub) {
    case 'install':
      return _handleInstall(rest, args)
    case 'list':
      return _handleList(args)
    case 'uninstall':
      return _handleUninstall(rest, args)
    case 'pipa-text':
      return _handlePipaText()
    case '':
      return { acknowledgement: _USAGE_KO }
    default:
      return {
        acknowledgement: `알 수 없는 subcommand: ${sub}\n${_USAGE_KO}`,
      }
  }
}

const pluginCommand: CommandDefinition = {
  name: 'plugin',
  description: 'Install / list / uninstall KOSMOS plugins',
  argumentHint: '<install|list|uninstall|pipa-text> [name]',
  handle,
}

export default pluginCommand
