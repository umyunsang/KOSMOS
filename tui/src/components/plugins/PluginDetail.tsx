// SPDX-License-Identifier: Apache-2.0
// Spec 1979 T026 — PluginDetail modal sub-component.
//
// Rendered by REPL.tsx when the citizen presses `i` while the
// PluginBrowser is mounted. Surfaces the manifest summary including PIPA
// §26 trustee acknowledgment SHA-256 for processes_pii=true plugins so
// citizens can verify who handles their data per FR-012.

import { Box, Text, useInput } from 'ink';
import React from 'react';
import { useTheme } from '../../theme/provider.js';
import type { PluginEntry } from './PluginBrowser.js';

export type PluginDetailProps = {
  /** The plugin to render details for. */
  plugin: PluginEntry;
  /** Optional PIPA acknowledgment SHA-256 (when processes_pii=true). */
  acknowledgment_sha256?: string | null;
  /** Called when Esc is pressed. */
  onDismiss: () => void;
};

const _LAYER_COLOR: Record<1 | 2 | 3, string> = {
  1: 'green',
  2: 'yellow',
  3: 'red',
};

/**
 * Detail modal for a single plugin. Closes on Esc.
 */
export function PluginDetail({
  plugin,
  acknowledgment_sha256 = null,
  onDismiss,
}: PluginDetailProps): React.ReactElement {
  const theme = useTheme();
  const layer = plugin.layer;
  const layerColor = layer ? _LAYER_COLOR[layer] : theme.subtle;
  const tierLabel = plugin.tier === 'live' ? 'Live' : plugin.tier === 'mock' ? 'Mock' : '—';
  const installedAt = plugin.install_timestamp_iso ?? '—';

  useInput((_input, key) => {
    if (key.escape) {
      onDismiss();
    }
  });

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      <Box marginBottom={1}>
        <Text bold color={theme.kosmosCore}>{'✻ '}</Text>
        <Text bold color={theme.wordmark}>{plugin.name}</Text>
        <Text color={theme.subtle}>{` v${plugin.version} [${tierLabel}]`}</Text>
      </Box>

      <Box flexDirection="column" paddingLeft={2}>
        <Box>
          <Text color={theme.subtle}>{'티어 (Tier): '}</Text>
          <Text>{plugin.tier ?? '—'}</Text>
        </Box>
        {layer ? (
          <Box>
            <Text color={theme.subtle}>{'권한 레벨 (Layer): '}</Text>
            <Text color={layerColor}>{`Layer ${layer}`}</Text>
          </Box>
        ) : null}
        <Box>
          <Text color={theme.subtle}>{'PII 처리: '}</Text>
          <Text>{plugin.trustee_org_name ? '예' : '아니오'}</Text>
        </Box>
        {plugin.trustee_org_name ? (
          <Box>
            <Text color={theme.subtle}>{'수탁 기관 (Trustee): '}</Text>
            <Text>{plugin.trustee_org_name}</Text>
          </Box>
        ) : null}
        <Box>
          <Text color={theme.subtle}>{'설치 일시 (Installed): '}</Text>
          <Text>{installedAt}</Text>
        </Box>
        {plugin.search_hint_ko ? (
          <Box>
            <Text color={theme.subtle}>{'검색어 (ko): '}</Text>
            <Text>{plugin.search_hint_ko}</Text>
          </Box>
        ) : null}
        {plugin.search_hint_en ? (
          <Box>
            <Text color={theme.subtle}>{'검색어 (en): '}</Text>
            <Text>{plugin.search_hint_en}</Text>
          </Box>
        ) : null}

        {/* PIPA §26 acknowledgment hash — only when PII is handled */}
        {acknowledgment_sha256 ? (
          <Box marginTop={1} flexDirection="column">
            <Text color={theme.subtle}>{'PIPA §26 수탁자 동의 해시 (acknowledgment SHA-256):'}</Text>
            <Text>{`  ${acknowledgment_sha256.slice(0, 32)}…`}</Text>
            <Text color={theme.subtle}>{'  See: docs/plugins/security-review.md'}</Text>
          </Box>
        ) : null}

        <Box marginTop={1} flexDirection="column">
          <Text color={theme.subtle}>{'설명:'}</Text>
          <Text>{`  ${plugin.description_ko}`}</Text>
        </Box>
      </Box>

      <Box marginTop={1}>
        <Text dimColor>{'Esc · 닫기 (dismiss)'}</Text>
      </Box>
    </Box>
  );
}
