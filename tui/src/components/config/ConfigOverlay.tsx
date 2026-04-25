// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/components/InvalidConfigDialog.tsx (CC 2.1.88, research-use)
// Spec 1635 P4 UI L2 — T062 ConfigOverlay (FR-030, US5).
//
// Non-secret configuration overlay.  Renders editable non-secret KOSMOS_*
// settings with inline arrow-key navigation.  Secret / .env-file items
// are represented as locked entries that open EnvSecretIsolatedEditor (T063).
//
// Structural shape borrowed from InvalidConfigDialog (Dialog + Select primitive)
// with navigation stripped to a simple key-driven list.

import React, { useState, useCallback } from 'react';
import { Box, Text, useInput } from 'ink';
import { useTheme } from '../../theme/provider.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConfigEntry = {
  key: string;
  label_ko: string;
  label_en: string;
  value: string;
  isSecret: boolean;
};

export type ConfigOverlayProps = {
  /** Current configuration entries to display */
  entries: ConfigEntry[];
  /** Called when the citizen confirms edits */
  onSave: (updated: ConfigEntry[]) => void;
  /** Called when the citizen cancels (Escape) */
  onCancel: () => void;
  /** Called when the citizen requests .env secret isolation (Shift+Enter on a secret) */
  onOpenSecretEditor: (key: string) => void;
};

// ---------------------------------------------------------------------------
// ConfigOverlay (T062)
// ---------------------------------------------------------------------------

/**
 * Inline configuration overlay for non-secret KOSMOS settings (FR-030).
 *
 * Navigation:
 *   ↑/↓  move selection
 *   Enter  edit selected (non-secret) or open secret-editor for secret entries
 *   Esc   cancel + close
 *   s     save current edits
 *
 * Secret entries are displayed with a lock indicator and cannot be edited
 * inline — they route to EnvSecretIsolatedEditor (T063).
 */
export function ConfigOverlay({
  entries,
  onSave,
  onCancel,
  onOpenSecretEditor,
}: ConfigOverlayProps): React.ReactElement {
  const theme = useTheme();
  const i18n = useUiL2I18n();
  const locale = (process.env['KOSMOS_TUI_LOCALE'] ?? 'ko') as 'ko' | 'en';

  const [cursor, setCursor] = useState(0);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editBuffer, setEditBuffer] = useState('');
  const [localEntries, setLocalEntries] = useState<ConfigEntry[]>(entries);

  const clampCursor = (c: number) => Math.min(Math.max(0, c), localEntries.length - 1);

  const handleInput = useCallback(
    (input: string, key: { upArrow: boolean; downArrow: boolean; return: boolean; escape: boolean; backspace: boolean; delete: boolean; ctrl: boolean }) => {
      // Editing mode
      if (editingKey !== null) {
        if (key.escape) {
          setEditingKey(null);
          setEditBuffer('');
          return;
        }
        if (key.return) {
          setLocalEntries((prev) =>
            prev.map((e) =>
              e.key === editingKey ? { ...e, value: editBuffer } : e,
            ),
          );
          setEditingKey(null);
          setEditBuffer('');
          return;
        }
        if (key.backspace || key.delete) {
          setEditBuffer((s) => s.slice(0, -1));
          return;
        }
        if (!key.ctrl && input.length > 0) {
          setEditBuffer((s) => s + input);
        }
        return;
      }

      // Navigation mode
      if (key.upArrow) { setCursor((c) => clampCursor(c - 1)); return; }
      if (key.downArrow) { setCursor((c) => clampCursor(c + 1)); return; }
      if (key.escape) { onCancel(); return; }
      if (key.return) {
        const entry = localEntries[cursor];
        if (!entry) return;
        if (entry.isSecret) {
          onOpenSecretEditor(entry.key);
        } else {
          setEditingKey(entry.key);
          setEditBuffer(entry.value);
        }
        return;
      }
      if (input === 's' || input === 'S') {
        onSave(localEntries);
        return;
      }
    },
    [editingKey, editBuffer, cursor, localEntries, onCancel, onSave, onOpenSecretEditor],
  );

  useInput(handleInput);

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1} borderStyle="round" borderColor={theme.kosmosCore}>
      {/* Title */}
      <Box marginBottom={1}>
        <Text bold color={theme.kosmosCore}>
          {'✻ '}
        </Text>
        <Text bold color={theme.wordmark}>
          {i18n.configOverlayTitle}
        </Text>
      </Box>

      {/* Entry list */}
      {localEntries.map((entry, idx) => {
        const isSelected = idx === cursor;
        const label = locale === 'en' ? entry.label_en : entry.label_ko;
        const isEditing = editingKey === entry.key;
        const displayValue = isEditing ? editBuffer : entry.value;

        return (
          <Box key={entry.key} paddingLeft={1} marginBottom={0}>
            <Box width={30} flexShrink={0}>
              <Text
                bold={isSelected}
                color={isSelected ? theme.kosmosCore : theme.text}
              >
                {isSelected ? '› ' : '  '}
                {entry.isSecret ? '🔒 ' : ''}
                {label}
              </Text>
            </Box>
            <Box flexGrow={1}>
              {entry.isSecret ? (
                <Text color={theme.subtle}>{'[hidden — Enter to edit in isolated mode]'}</Text>
              ) : isEditing ? (
                <Text color={theme.wordmark} underline>
                  {`${displayValue}█`}
                </Text>
              ) : (
                <Text color={theme.text}>{displayValue || '(empty)'}</Text>
              )}
            </Box>
          </Box>
        );
      })}

      {/* Footer */}
      <Box marginTop={1}>
        <Text dimColor>
          {'↑↓ navigate · Enter edit · s save · Esc cancel'}
        </Text>
      </Box>
    </Box>
  );
}
