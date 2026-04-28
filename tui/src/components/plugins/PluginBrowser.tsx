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
  // Spec 1979 T024 — additive optional fields, backwards compatible with
  // existing Spec 1635 T065 callers that only populate the original 6 fields.
  tier?: 'live' | 'mock';
  layer?: 1 | 2 | 3;
  trustee_org_name?: string | null;
  install_timestamp_iso?: string;
  search_hint_ko?: string;
  search_hint_en?: string;
};

/**
 * Spec 1979 T029 — in-flight install placeholder row.
 *
 * Each entry represents a plugin currently being installed (via the backend
 * dispatcher's plugin_op_progress stream); the browser renders an
 * "(설치 중… 단계 N/7)" placeholder for each until the matching
 * plugin_op_complete arrives at which point the parent removes the entry
 * and refetches the plugin list to surface the newly-registered tool.
 */
export type InflightInstallEntry = {
  /** Catalog name (matches plugin_op_request.name). */
  name: string;
  /** Current install phase (1-7). */
  phase: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  /** Korean-primary phase message from PluginOpFrame.progress_message_ko. */
  message_ko?: string;
};

export type PluginBrowserProps = {
  /** Current plugin list */
  plugins: PluginEntry[];
  /** Spec 1979 T029 — in-flight installs being tracked by the parent. */
  inflightInstalls?: InflightInstallEntry[];
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
// Glyphs (FR-031 + FR-036) + Spec 1979 T025 layer color glyph (UI-C.1)
// ---------------------------------------------------------------------------

const GLYPH_ACTIVE   = '⏺'; // CC thread glyph — active plugin
const GLYPH_INACTIVE = '○'; // empty circle — inactive plugin

// Spec 1979 T025 — Layer color glyphs per kosmos-migration-tree.md UI-C.1.
// Layer 1 = green ⓵ (low-risk, public-data lookup)
// Layer 2 = orange ⓶ (medium-risk, citizen-personal lookup)
// Layer 3 = red ⓷ (high-risk, irreversible / write actions)
const LAYER_GLYPH: Record<1 | 2 | 3, string> = {
  1: '⓵',
  2: '⓶',
  3: '⓷',
};

function _layerColor(layer: 1 | 2 | 3, theme: ReturnType<typeof useTheme>): string {
  // Theme palette mapping — falls back to plain ANSI codes when the theme
  // doesn't define explicit layer colors.
  if (layer === 1) return (theme.success ?? theme.kosmosCore) || 'green';
  if (layer === 2) return (theme.warning ?? theme.subtle) || 'yellow';
  return (theme.error ?? theme.subtle) || 'red';
}

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
  inflightInstalls = [],
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

      {/* Spec 1979 T029 — in-flight install placeholder rows render BEFORE
          the installed list so citizens see the active operation prominently. */}
      {inflightInstalls.map((entry) => (
        <Box key={`inflight-${entry.name}`} marginBottom={0}>
          <Box width={3} flexShrink={0}>
            <Text color={theme.subtle}>{'⏳'}</Text>
          </Box>
          <Box width={24} flexShrink={0}>
            <Text color={theme.subtle}>{`  ${entry.name}`}</Text>
          </Box>
          <Box flexGrow={1}>
            <Text color={theme.subtle}>
              {entry.message_ko
                ? `(설치 중… 단계 ${entry.phase}/7 · ${entry.message_ko})`
                : `(설치 중… 단계 ${entry.phase}/7)`}
            </Text>
          </Box>
        </Box>
      ))}

      {/* Plugin list */}
      {plugins.length === 0 && inflightInstalls.length === 0 ? (
        <Box paddingLeft={2}>
          <Text dimColor>{'플러그인이 없습니다 · No plugins installed'}</Text>
        </Box>
      ) : (
        plugins.map((plugin, idx) => {
          const isSelected = idx === cursor;
          const description = locale === 'en' ? plugin.description_en : plugin.description_ko;
          const glyph = plugin.isActive ? GLYPH_ACTIVE : GLYPH_INACTIVE;
          const glyphColor = plugin.isActive ? theme.kosmosCore : theme.inactive;

          // Spec 1979 T025 — additive optional fields surface as inline columns
          // when populated (Spec 1635 T065 callers without these fields keep
          // the original 3-column layout).
          const tierBadge = plugin.tier
            ? `[${plugin.tier === 'live' ? 'Live' : 'Mock'}]`
            : '';
          const layer = plugin.layer;
          const layerGlyph = layer ? LAYER_GLYPH[layer] : '';
          const layerColor = layer ? _layerColor(layer, theme) : theme.subtle;
          const trustee = plugin.trustee_org_name ?? null;

          return (
            <Box key={plugin.id} marginBottom={0}>
              {/* Status glyph (⏺/○) */}
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

              {/* T025 — Tier badge ([Live] / [Mock]) */}
              {tierBadge ? (
                <Box width={7} flexShrink={0}>
                  <Text color={theme.subtle}>{tierBadge}</Text>
                </Box>
              ) : null}

              {/* T025 — Layer color glyph (⓵/⓶/⓷) */}
              {layerGlyph ? (
                <Box width={3} flexShrink={0}>
                  <Text color={layerColor}>{layerGlyph}</Text>
                </Box>
              ) : null}

              {/* Description */}
              <Box flexGrow={1}>
                <Text color={theme.subtle} wrap="truncate-end">
                  {description}
                </Text>
              </Box>

              {/* T025 — Trustee org (right-aligned, only when PII-handling) */}
              {trustee ? (
                <Box flexShrink={0} marginLeft={1}>
                  <Text color={theme.subtle}>{`(${trustee})`}</Text>
                </Box>
              ) : null}
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
