// SPDX-License-Identifier: Apache-2.0
//
// `/plugin <subcommand>` slash command — KOSMOS citizen plugin lifecycle.
//
// Spec 1979 T021 wired this file as the `/plugin` slash command (replacing
// the CC marketplace residue at `./commands/plugin/index.tsx`). This file
// MUST conform to the global Command type union (PromptCommand | LocalCommand
// | LocalJSXCommand) declared in tui/src/types/command.ts — earlier drafts
// used a `handle()` shape from the permission-router framework which the
// global slash-command dispatcher does NOT consume; the result was that
// `/plugin install seoul-subway` typed correctly into the prompt but the
// command never executed.
//
// We use LocalJSXCommand:
//   - The actual citizen-visible work is emitting a `plugin_op_request`
//     IPC frame (consumed by the backend dispatcher in
//     src/kosmos/ipc/plugin_op_dispatcher.py).
//   - LocalJSX `call(onDone, context, args)` returns a React.ReactNode
//     that's mounted into toolJSX. We mount a tiny status banner that
//     immediately calls `onDone(acknowledgement)` so the citizen sees the
//     "🔄 ${name} 플러그인 설치 시작..." text in their conversation feed.
//
// Subcommands per migration tree § B8 + contracts/plugin-install.cli.md:
//   /plugin install <name> [--version v]
//   /plugin list
//   /plugin uninstall <name>
//   /plugin pipa-text                 — print canonical PIPA §26 text + hash

import * as React from 'react';

import type { Command, LocalJSXCommandModule } from '../types/command.js';
import { CANONICAL_PIPA_ACK_SHA256 } from '../ipc/pipa.generated.js';
import { getOrCreateKosmosBridge, getKosmosBridgeSessionId } from '../ipc/bridgeSingleton.js';

const _USAGE_KO =
  '사용법: /plugin <install|list|uninstall|pipa-text> [...]';

function _newCorrelationId(): string {
  return crypto.randomUUID();
}

function _now(): string {
  return new Date().toISOString();
}

function _parseSubcommand(raw: string): { sub: string; rest: string } {
  const trimmed = raw.trim();
  if (trimmed.length === 0) return { sub: '', rest: '' };
  const space = trimmed.indexOf(' ');
  if (space === -1) return { sub: trimmed, rest: '' };
  return { sub: trimmed.slice(0, space), rest: trimmed.slice(space + 1).trim() };
}

function _parseInstallArgs(rest: string): {
  name: string | undefined;
  version: string | undefined;
  dryRun: boolean;
} {
  const tokens = rest.split(/\s+/).filter((t) => t.length > 0);
  let name: string | undefined;
  let version: string | undefined;
  let dryRun = false;
  for (let i = 0; i < tokens.length; i += 1) {
    const tok = tokens[i];
    if (!tok) continue;
    if (tok === '--version') {
      version = tokens[i + 1];
      i += 1;
    } else if (tok === '--dry-run') {
      dryRun = true;
    } else if (!name && !tok.startsWith('--')) {
      name = tok;
    }
  }
  return { name, version, dryRun };
}

function _emitPluginOp(payload: Record<string, unknown>): void {
  const bridge = getOrCreateKosmosBridge();
  const sessionId = getKosmosBridgeSessionId();
  const frame = {
    kind: 'plugin_op',
    version: '1.0',
    session_id: sessionId,
    correlation_id: _newCorrelationId(),
    ts: _now(),
    role: 'tui',
    op: 'request',
    ...payload,
  };
  bridge.send(frame as never);
}

// ---------------------------------------------------------------------------
// LocalJSXCommand `call` implementation
// ---------------------------------------------------------------------------

const call: LocalJSXCommandModule['call'] = async (onDone, _context, args) => {
  const { sub, rest } = _parseSubcommand(args);

  let acknowledgement: string;

  if (sub === 'install') {
    const { name, version, dryRun } = _parseInstallArgs(rest);
    if (!name) {
      acknowledgement = '플러그인 이름이 필요합니다: /plugin install <name>';
    } else {
      _emitPluginOp({
        request_op: 'install',
        name,
        requested_version: version ?? null,
        dry_run: dryRun,
      });
      const dryNote = dryRun ? ' (dry-run)' : '';
      acknowledgement = `🔄 ${name} 플러그인 설치 시작...${dryNote}`;
    }
  } else if (sub === 'list') {
    _emitPluginOp({ request_op: 'list' });
    acknowledgement = '📋 설치된 플러그인 목록 조회 중...';
  } else if (sub === 'uninstall') {
    const name = rest.trim().split(/\s+/)[0];
    if (!name) {
      acknowledgement = '플러그인 이름이 필요합니다: /plugin uninstall <name>';
    } else {
      _emitPluginOp({ request_op: 'uninstall', name });
      acknowledgement = `🗑️ ${name} 플러그인 제거 시작...`;
    }
  } else if (sub === 'pipa-text') {
    acknowledgement = [
      'PIPA §26 trustee acknowledgment canonical SHA-256:',
      `  ${CANONICAL_PIPA_ACK_SHA256}`,
      'Source: docs/plugins/security-review.md (마커 사이 텍스트)',
      'manifest.yaml 의 acknowledgment_sha256 필드에 위 값을 그대로 기록하세요.',
    ].join('\n');
  } else if (sub === '') {
    acknowledgement = _USAGE_KO;
  } else {
    acknowledgement = `알 수 없는 subcommand: ${sub}\n${_USAGE_KO}`;
  }

  // LocalJSX commands return a React node mounted into toolJSX. We use
  // null + immediately call onDone so the citizen sees the acknowledgement
  // in their conversation feed (added as a notification by handlePromptSubmit).
  // `display: 'system'` renders the text as a system-style notification.
  setTimeout(() => onDone(acknowledgement, { display: 'system' }), 0);
  return null;
};

const pluginCommand: Command = {
  type: 'local-jsx',
  name: 'plugin',
  description: 'KOSMOS 플러그인 설치 / 목록 / 제거 / PIPA 해시 (Install / list / uninstall KOSMOS plugins)',
  argumentHint: '<install|list|uninstall|pipa-text> [name]',
  immediate: true,
  load: async () => ({ call }),
};

export default pluginCommand;
