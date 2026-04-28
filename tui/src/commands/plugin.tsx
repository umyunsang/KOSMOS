// SPDX-License-Identifier: Apache-2.0
//
// Source pattern: .references/claude-code-sourcemap/restored-src/src/commands/plugin/{index.tsx,plugin.tsx}
//   CC 2.1.88's plugin command:
//     1. index.tsx — Command def with type=local-jsx, name=plugin
//     2. plugin.tsx — call() returns <PluginSettings onComplete={onDone} args={args} />
//
//   The pattern: call() returns a React component; the component handles all
//   interaction internally (consent, progress, completion); component
//   unmounts via onDone after terminal state. CC's marketplace surface
//   is replaced by KOSMOS's PluginInstallFlow (see ../components/plugins/).
//
// Spec 1979 — citizen plugin lifecycle slash command.
//
// Subcommands (per migration tree § B8 + contracts/plugin-install.cli.md):
//   /plugin install <name> [--version v] [--dry-run]
//   /plugin list
//   /plugin uninstall <name>
//   /plugin pipa-text                 — print canonical PIPA §26 hash

import * as React from 'react';

import type { Command, LocalJSXCommandModule } from '../types/command.js';
import { CANONICAL_PIPA_ACK_SHA256 } from '../ipc/pipa.generated.js';
import { PluginInstallFlow } from '../components/plugins/PluginInstallFlow.js';

const _USAGE_KO =
  '사용법: /plugin <install|list|uninstall|pipa-text> [...]';

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

// ---------------------------------------------------------------------------
// LocalJSXCommand `call` — mirrors CC's pattern of returning a React component
// ---------------------------------------------------------------------------

const call: LocalJSXCommandModule['call'] = async (onDone, _context, args) => {
  const { sub, rest } = _parseSubcommand(args ?? '');

  // Non-interactive subcommands fire onDone immediately + return null.
  if (sub === 'pipa-text') {
    const text = [
      'PIPA §26 trustee acknowledgment canonical SHA-256:',
      `  ${CANONICAL_PIPA_ACK_SHA256}`,
      'Source: docs/plugins/security-review.md (마커 사이 텍스트)',
      'manifest.yaml 의 acknowledgment_sha256 필드에 위 값을 그대로 기록하세요.',
    ].join('\n');
    setTimeout(() => onDone(text, { display: 'system' }), 0);
    return null;
  }

  if (sub === '') {
    setTimeout(() => onDone(_USAGE_KO, { display: 'system' }), 0);
    return null;
  }

  if (sub === 'install') {
    const { name, version, dryRun } = _parseInstallArgs(rest);
    if (!name) {
      setTimeout(
        () => onDone('플러그인 이름이 필요합니다: /plugin install <name>', { display: 'system' }),
        0,
      );
      return null;
    }
    return (
      <PluginInstallFlow
        sub="install"
        name={name}
        requestedVersion={version}
        dryRun={dryRun}
        onComplete={onDone}
      />
    );
  }

  if (sub === 'uninstall') {
    const targetName = rest.trim().split(/\s+/)[0];
    if (!targetName) {
      setTimeout(
        () => onDone('플러그인 이름이 필요합니다: /plugin uninstall <name>', { display: 'system' }),
        0,
      );
      return null;
    }
    return <PluginInstallFlow sub="uninstall" name={targetName} onComplete={onDone} />;
  }

  if (sub === 'list') {
    return <PluginInstallFlow sub="list" onComplete={onDone} />;
  }

  // Unknown subcommand
  setTimeout(
    () => onDone(`알 수 없는 subcommand: ${sub}\n${_USAGE_KO}`, { display: 'system' }),
    0,
  );
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
