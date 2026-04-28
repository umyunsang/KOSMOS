// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/components/CustomSelect/ (CC 2.1.88, research-use)
// Spec 1635 P4 UI L2 — T065 PluginBrowser (FR-031, US5).
//
// Plugin browser with ⏺ active / ○ inactive toggles and keybindings:
//   Space  toggle activation
//   i      show detail view
//   r      remove plugin
//   a      open marketplace entry-point
//
// Structural shape mirrors CC CustomSelect list with a fixed-left status glyph
// column and right-aligned action hints (FR-034 / SC-009 ≥90% visual fidelity).
//
// Keybindings are consumed locally via useInput while the overlay is mounted.
// The Plugin context in defaultBindings.ts (space/i/r/a) mirrors this surface.

import React, { useState, useCallback } from 'react';
import { Box, Text, useInput } from 'ink';
import { useTheme } from '../../theme/provider.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PluginEntry = {
  id: string;
  name: string;
  version: string;
  description_ko: string;
  description_en: string;
  isActive: boolean;
};

export type PluginBrowserProps = {
  /** Current plugin list */
  plugins: PluginEntry[];
  /** Called when toggle is confirmed */
  onToggle: (id: string, newActive: boolean) => void;
  /** Called when the citizen requests detail view for a plugin */
  onDetail: (id: string) => void;
  /** Called when the citizen requests plugin removal */
  onRemove: (id: string) => void;
  /** Called when the citizen presses 'a' to open the marketplace */
  onMarketplace: () => void;
  /** Called when Escape is pressed */
  onDismiss: () => void;
};

// ---------------------------------------------------------------------------
// Glyphs (FR-031 + FR-036)
// ---------------------------------------------------------------------------

const GLYPH_ACTIVE   = '⏺'; // CC thread glyph — active plugin
const GLYPH_INACTIVE = '○'; // empty circle — inactive plugin

// ---------------------------------------------------------------------------
// PluginBrowser (T065)
// ---------------------------------------------------------------------------

/**
 * Plugin browser with ⏺/○ status and Space/i/r/a keybindings (FR-031).
 *
 * Layout (approximate):
 *   ⏺  Plugin Name  v1.0  Description text…         Space/i/r/a
 *   ○  Another Plugin v0.5  A different description…
 */
export function PluginBrowser({
  plugins,
  onToggle,
  onDetail,
  onRemove,
  onMarketplace,
  onDismiss,
}: PluginBrowserProps): React.ReactElement {
  const theme = useTheme();
  const i18n = useUiL2I18n();
  const locale = (process.env['KOSMOS_TUI_LOCALE'] ?? 'ko') as 'ko' | 'en';

  const [cursor, setCursor] = useState(0);
  // Spec 1979 T028 — `a` keystroke renders a deferred-to-#1820 banner inline
  // rather than a no-op so citizens see why the marketplace catalog browser
  // is unavailable. The banner clears on next keypress.
  const [marketplaceDeferredVisible, setMarketplaceDeferredVisible] =
    useState<boolean>(false);
  const clamp = (n: number) => Math.min(Math.max(0, n), Math.max(0, plugins.length - 1));

  const handleInput = useCallback(
    (input: string, key: { upArrow: boolean; downArrow: boolean; escape: boolean; ctrl: boolean }) => {
      // Any keypress after a deferred banner clears it.
      if (marketplaceDeferredVisible) {
        setMarketplaceDeferredVisible(false);
      }
      if (key.escape) { onDismiss(); return; }
      if (key.upArrow) { setCursor((c) => clamp(c - 1)); return; }
      if (key.downArrow) { setCursor((c) => clamp(c + 1)); return; }

      const entry = plugins[cursor];
      if (!entry) return;

      if (input === ' ') {
        // Space: toggle activation
        onToggle(entry.id, !entry.isActive);
        return;
      }
      if (input === 'i' || input === 'I') {
        onDetail(entry.id);
        return;
      }
      if (input === 'r' || input === 'R') {
        onRemove(entry.id);
        return;
      }
      if (input === 'a' || input === 'A') {
        // Spec 1979 T028 — show deferred banner then invoke parent callback
        // (kept for caller telemetry; the banner is the citizen-visible UX).
        setMarketplaceDeferredVisible(true);
        onMarketplace();
        return;
      }
    },
    [cursor, plugins, onToggle, onDetail, onRemove, onMarketplace, onDismiss, marketplaceDeferredVisible],
  );

  useInput(handleInput);

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      {/* Title */}
      <Box marginBottom={1}>
        <Text bold color={theme.kosmosCore}>{'✻ '}</Text>
        <Text bold color={theme.wordmark}>{i18n.pluginBrowserTitle}</Text>
      </Box>

      {/* Plugin list */}
      {plugins.length === 0 ? (
        <Box paddingLeft={2}>
          <Text dimColor>{'플러그인이 없습니다 · No plugins installed'}</Text>
        </Box>
      ) : (
        plugins.map((plugin, idx) => {
          const isSelected = idx === cursor;
          const description = locale === 'en' ? plugin.description_en : plugin.description_ko;
          const glyph = plugin.isActive ? GLYPH_ACTIVE : GLYPH_INACTIVE;
          const glyphColor = plugin.isActive ? theme.kosmosCore : theme.inactive;

          return (
            <Box key={plugin.id} marginBottom={0}>
              {/* Status glyph */}
              <Box width={3} flexShrink={0}>
                <Text color={glyphColor}>{glyph}</Text>
              </Box>

              {/* Name + version */}
              <Box width={24} flexShrink={0}>
                <Text bold={isSelected} color={isSelected ? theme.kosmosCore : theme.text}>
                  {isSelected ? '› ' : '  '}
                  {plugin.name}
                </Text>
                <Text color={theme.subtle}>{` v${plugin.version}`}</Text>
              </Box>

              {/* Description */}
              <Box flexGrow={1}>
                <Text color={theme.subtle} wrap="truncate-end">
                  {description}
                </Text>
              </Box>
            </Box>
          );
        })
      )}

      {/* Spec 1979 T028 — deferred banner for `a` keystroke */}
      {marketplaceDeferredVisible ? (
        <Box marginTop={1}>
          <Text color={theme.subtle}>
            {'⚠ 스토어 브라우저는 #1820 에서 작업 중입니다 (deferred) · Marketplace browser deferred to #1820'}
          </Text>
        </Box>
      ) : null}

      {/* Keybinding hint (FR-031) */}
      <Box marginTop={1}>
        <Text dimColor>{i18n.pluginToggleHint}</Text>
      </Box>
      <Box>
        <Text dimColor>{'Esc · 닫기 (dismiss)'}</Text>
      </Box>
    </Box>
  );
}
