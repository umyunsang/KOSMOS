// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — Slash command catalog SSOT (FR-014/029, T010).
//
// Single source of truth consumed by:
// - autocomplete dropdown (FR-014, tui/src/components/PromptInput/PromptInputFooterSuggestions.tsx)
// - /help 4-group output (FR-029, tui/src/components/help/HelpV2Grouped.tsx)
//
// Schema: tui/src/schemas/ui-l2/slash-command.ts
//         specs/1635-ui-l2-citizen-port/contracts/slash-commands.schema.json
import {
  type SlashCommandCatalogEntryT,
  type SlashCommandGroupT,
} from '../schemas/ui-l2/slash-command.js';

export const UI_L2_SLASH_COMMANDS: readonly SlashCommandCatalogEntryT[] = [
  {
    name: '/onboarding',
    group: 'session',
    description_ko: '온보딩 시퀀스를 처음부터 다시 진행합니다',
    description_en: 'Restart onboarding from step 1',
    arg_signature: '[step-name]',
    hidden: false,
  },
  {
    name: '/lang',
    group: 'session',
    description_ko: '언어를 한국어/영어로 전환합니다',
    description_en: 'Switch language between Korean and English',
    arg_signature: 'ko|en',
    hidden: false,
  },
  {
    name: '/consent list',
    group: 'permission',
    description_ko: '본 세션의 권한 영수증 목록을 표시합니다',
    description_en: 'List permission receipts for the current session',
    arg_signature: null,
    hidden: false,
  },
  {
    name: '/consent revoke',
    group: 'permission',
    description_ko: '발급된 권한 영수증을 철회합니다',
    description_en: 'Revoke a previously granted permission receipt',
    arg_signature: 'rcpt-<id>',
    hidden: false,
  },
  {
    name: '/agents',
    group: 'tool',
    description_ko: '활성 부처 에이전트 상태를 표시합니다',
    description_en: 'Show active ministry agent status',
    arg_signature: '[--detail]',
    hidden: false,
  },
  {
    name: '/help',
    group: 'session',
    description_ko: '명령 목록을 4개 그룹으로 묶어 표시합니다',
    description_en: 'Show commands grouped into four sections',
    arg_signature: null,
    hidden: false,
  },
  {
    name: '/config',
    group: 'storage',
    description_ko: '설정 오버레이를 엽니다 (.env 비밀값은 격리 편집)',
    description_en: 'Open configuration overlay (.env secrets isolated)',
    arg_signature: null,
    hidden: false,
  },
  {
    name: '/plugins',
    group: 'tool',
    description_ko: '플러그인 브라우저를 엽니다',
    description_en: 'Open the plugin browser',
    arg_signature: null,
    hidden: false,
  },
  {
    name: '/export',
    group: 'storage',
    description_ko: '대화·도구·영수증을 PDF로 내보냅니다',
    description_en: 'Export conversation + tools + receipts to PDF',
    arg_signature: null,
    hidden: false,
  },
  {
    name: '/history',
    group: 'storage',
    description_ko: '과거 세션을 날짜·세션·Layer 필터로 검색합니다',
    description_en: 'Search past sessions by date / session / layer filter',
    arg_signature: '[--date FROM..TO] [--session <id>] [--layer <n>]',
    hidden: false,
  },
];

export function findCatalogEntry(name: string): SlashCommandCatalogEntryT | undefined {
  return UI_L2_SLASH_COMMANDS.find((e) => e.name === name);
}

export function entriesInGroup(group: SlashCommandGroupT): SlashCommandCatalogEntryT[] {
  return UI_L2_SLASH_COMMANDS.filter((e) => e.group === group && !e.hidden);
}

/**
 * Prefix-match helper for the autocomplete dropdown (FR-014). Matches on
 * the command name only; the dropdown component owns highlight rendering.
 */
export function matchPrefix(prefix: string): SlashCommandCatalogEntryT[] {
  const p = prefix.trim().toLowerCase();
  if (p === '' || p === '/') return [...UI_L2_SLASH_COMMANDS].filter((e) => !e.hidden);
  return UI_L2_SLASH_COMMANDS.filter((e) => !e.hidden && e.name.toLowerCase().startsWith(p));
}
