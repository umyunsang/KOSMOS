// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — SlashCommandSuggestions component (FR-014, T021).
//
// Autocomplete dropdown that activates the moment the citizen types `/`.
// Driven by `matchPrefix()` from the slash-command catalog SSOT (T010).
// Shows highlighted match + inline preview per migration tree §UI-B.6.
//
// Source reference: cc:components/ContextSuggestions.tsx (autocomplete
// inspiration) + existing PromptInputFooterSuggestions dropdown primitive.
// KOSMOS adaptation: consumes UI_L2_SLASH_COMMANDS / matchPrefix() from
// catalog.ts; maps SlashCommandCatalogEntryT to SuggestionItem shape.

import React from 'react';
import { useContext } from 'react';
import { Box, Text } from '../../ink.js';
import { TerminalSizeContext } from '../../ink/components/TerminalSizeContext.js';
import { stringWidth } from '../../ink/stringWidth.js';
import {
  matchPrefix,
  UI_L2_SLASH_COMMANDS,
} from '../../commands/catalog.js';
import type { SlashCommandCatalogEntryT } from '../../schemas/ui-l2/slash-command.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Maximum items to show in the dropdown (CC ContextSuggestions uses 5). */
const MAX_VISIBLE = 5;

// ---------------------------------------------------------------------------
// Helper — locale-aware description
// ---------------------------------------------------------------------------

function descriptionFor(entry: SlashCommandCatalogEntryT): string {
  const locale = (process.env['KOSMOS_TUI_LOCALE'] ?? 'ko') as 'ko' | 'en';
  return locale === 'en' ? entry.description_en : entry.description_ko;
}

// ---------------------------------------------------------------------------
// Single suggestion row
// ---------------------------------------------------------------------------

type SuggestionRowProps = {
  entry: SlashCommandCatalogEntryT;
  /** The raw prefix typed by the citizen (e.g. "/con") */
  prefix: string;
  isSelected: boolean;
  terminalWidth: number;
};

function SuggestionRow({
  entry,
  prefix,
  isSelected,
  terminalWidth,
}: SuggestionRowProps): React.ReactNode {
  const description = descriptionFor(entry);
  const argSig = entry.arg_signature ?? '';

  // Highlight the matching prefix portion of the command name.
  const matchLen = prefix.length;
  const matchedPart = entry.name.slice(0, matchLen);
  const restPart = entry.name.slice(matchLen);

  // Reserve space: name(up to 25) + ' ' + argSig(up to 15) + ' — ' + description
  const nameWidth = Math.min(stringWidth(entry.name), 25);
  const argWidth = argSig ? Math.min(stringWidth(argSig) + 1, 16) : 0;
  const descAvailable = Math.max(terminalWidth - nameWidth - argWidth - 6, 0);
  const truncDesc = description.length > descAvailable
    ? description.slice(0, Math.max(0, descAvailable - 1)) + '…'
    : description;

  const nameColor = isSelected ? 'green' : undefined;
  const dimColor = !isSelected;

  return (
    <Box flexDirection="row">
      {/* Matched prefix highlighted */}
      <Text color={isSelected ? 'green' : 'cyan'} bold={isSelected}>
        {matchedPart}
      </Text>
      {/* Rest of command name */}
      <Text color={nameColor} dimColor={!isSelected}>
        {restPart}
      </Text>
      {/* Arg signature */}
      {argSig && (
        <Text dimColor color="gray">
          {' '}{argSig}
        </Text>
      )}
      {/* Separator + description */}
      {truncDesc && (
        <Text dimColor>
          {' — '}{truncDesc}
        </Text>
      )}
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export type SlashCommandSuggestionsProps = {
  /** Current raw input text (e.g. "/con" or "/agents --d") */
  inputText: string;
  /** Currently selected index in the dropdown (0-based) */
  selectedIndex?: number;
  /** Called when the citizen selects an entry (e.g. via Tab / Enter) */
  onSelect?: (entry: SlashCommandCatalogEntryT) => void;
};

/**
 * SlashCommandSuggestions renders a dropdown of matching slash commands the
 * moment the citizen types `/`.  Hides when input doesn't start with `/`.
 *
 * Contract (FR-014):
 * - Appears within 100 ms of the `/` keystroke (SC-005); the component is
 *   purely synchronous — no async lookups.
 * - Shows highlighted match (matched prefix in a distinct color) + inline
 *   description preview.
 * - Driven by `matchPrefix()` from the catalog SSOT (T010 / catalog.ts).
 */
export function SlashCommandSuggestions({
  inputText,
  selectedIndex = 0,
}: SlashCommandSuggestionsProps): React.ReactNode {
  // Only activate when input starts with '/'
  if (!inputText.startsWith('/')) {
    return null;
  }

  const matches = matchPrefix(inputText);

  if (matches.length === 0) {
    return null;
  }

  return (
    <SlashCommandSuggestionsInner
      matches={matches}
      inputText={inputText}
      selectedIndex={selectedIndex}
    />
  );
}

/** Inner component — reads terminal size with safe fallback for test env. */
function SlashCommandSuggestionsInner({
  matches,
  inputText,
  selectedIndex,
}: {
  matches: SlashCommandCatalogEntryT[];
  inputText: string;
  selectedIndex: number;
}): React.ReactNode {
  // Use context directly to avoid the throw-on-null guard in useTerminalSize.
  // Falls back to 80 columns in test / non-Ink-App contexts.
  const size = useContext(TerminalSizeContext);
  const columns = size?.columns ?? 80;

  // Clamp selection to visible range
  const safeSelected = Math.min(
    Math.max(0, selectedIndex),
    matches.length - 1,
  );

  const startIndex = Math.max(
    0,
    Math.min(safeSelected - Math.floor(MAX_VISIBLE / 2), matches.length - MAX_VISIBLE),
  );
  const endIndex = Math.min(startIndex + MAX_VISIBLE, matches.length);
  const visible = matches.slice(startIndex, endIndex);

  return (
    <Box flexDirection="column" justifyContent="flex-end">
      {visible.map((entry, i) => (
        <SuggestionRow
          key={entry.name}
          entry={entry}
          prefix={inputText}
          isSelected={startIndex + i === safeSelected}
          terminalWidth={columns}
        />
      ))}
    </Box>
  );
}
