// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T061 /help command (FR-029, US5).
//
// Emits the 4-group help output sourced from UI_L2_SLASH_COMMANDS catalog.
// Calls emitSurfaceActivation('help') at command start per FR-037.
//
// This file replaces/extends the legacy help command wiring.

import { emitSurfaceActivation } from '../observability/surface.js';
import {
  groupCatalog,
  GROUP_ORDER,
  type SlashCommandGroupT,
} from '../schemas/ui-l2/slash-command.js';
import { UI_L2_SLASH_COMMANDS } from './catalog.js';
import { getUiL2I18n } from '../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type HelpCommandResult = {
  /** Formatted plain-text output for the REPL message stream */
  text: string;
  /** Grouped catalog snapshot for React rendering */
  groups: ReturnType<typeof groupCatalog>;
};

// ---------------------------------------------------------------------------
// Command handler (T061)
// ---------------------------------------------------------------------------

function groupLabel(group: SlashCommandGroupT, locale: 'ko' | 'en'): string {
  const i18n = getUiL2I18n(locale);
  switch (group) {
    case 'session':    return i18n.helpGroupSession;
    case 'permission': return i18n.helpGroupPermission;
    case 'tool':       return i18n.helpGroupTool;
    case 'storage':    return i18n.helpGroupStorage;
  }
}

/**
 * Execute the /help command.
 *
 * Emits `kosmos.ui.surface=help` (FR-037) and returns a grouped command
 * catalogue for both plain-text and React rendering paths.
 */
export function executeHelp(locale: 'ko' | 'en' = 'ko'): HelpCommandResult {
  // FR-037: emit surface activation at command start
  emitSurfaceActivation('help');

  const groups = groupCatalog(UI_L2_SLASH_COMMANDS);

  // Build plain-text representation for non-React rendering fallback
  const lines: string[] = [''];
  for (const group of GROUP_ORDER) {
    const label = groupLabel(group, locale);
    const entries = groups[group];
    if (entries.length === 0) continue;

    lines.push(`─── ${label} ───`);
    for (const entry of entries) {
      const sig = entry.arg_signature ? ` ${entry.arg_signature}` : '';
      const description = locale === 'en' ? entry.description_en : entry.description_ko;
      const nameWidth = 26;
      const fullName = `  ${entry.name}${sig}`;
      const padded = fullName.padEnd(nameWidth);
      lines.push(`${padded}  ${description}`);
    }
    lines.push('');
  }

  return {
    text: lines.join('\n'),
    groups,
  };
}
