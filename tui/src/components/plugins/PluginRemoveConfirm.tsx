// SPDX-License-Identifier: Apache-2.0
// Spec 1979 T027 — PluginRemoveConfirm modal sub-component.
//
// Rendered by REPL.tsx when the citizen presses `r` while the
// PluginBrowser is mounted. Y emits `plugin_op_request:uninstall` via the
// passed onConfirm callback; N dismisses without action.

import { Box, Text, useInput } from 'ink';
import React from 'react';
import { useTheme } from '../../theme/provider.js';
import type { PluginEntry } from './PluginBrowser.js';

export type PluginRemoveConfirmProps = {
  /** The plugin to remove. */
  plugin: PluginEntry;
  /** Called on Y — caller emits the plugin_op_request:uninstall frame. */
  onConfirm: (plugin: PluginEntry) => void;
  /** Called on N or Esc. */
  onCancel: () => void;
};

/**
 * Confirmation modal for plugin removal.
 *
 * Layout (approximate):
 *   ⚠ 플러그인 제거 확인
 *
 *     <plugin_name> v<version> 을 제거하시겠습니까?
 *     ⏺ 설치 디렉터리 삭제됨
 *     ⏺ 영수증 (uninstall) 추가됨
 *
 *   [Y 제거 / N 취소]
 */
export function PluginRemoveConfirm({
  plugin,
  onConfirm,
  onCancel,
}: PluginRemoveConfirmProps): React.ReactElement {
  const theme = useTheme();

  useInput((input, key) => {
    if (key.escape) {
      onCancel();
      return;
    }
    if (input === 'y' || input === 'Y') {
      onConfirm(plugin);
      return;
    }
    if (input === 'n' || input === 'N') {
      onCancel();
      return;
    }
  });

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      <Box marginBottom={1}>
        <Text bold color={theme.warning ?? 'yellow'}>{'⚠  '}</Text>
        <Text bold>{'플러그인 제거 확인 · Confirm plugin removal'}</Text>
      </Box>

      <Box flexDirection="column" paddingLeft={2} marginBottom={1}>
        <Text>{`${plugin.name} v${plugin.version} 을 제거하시겠습니까?`}</Text>
        <Box marginTop={1} flexDirection="column">
          <Text color={theme.subtle}>{'⏺ 설치 디렉터리: ~/.kosmos/memdir/user/plugins/<id>/'}</Text>
          <Text color={theme.subtle}>{'⏺ 영수증 (uninstall) 이 ~/.kosmos/memdir/user/consent/ 에 추가됩니다.'}</Text>
        </Box>
      </Box>

      <Box>
        <Text dimColor>{'[Y 제거 / N 취소 / Esc 취소]'}</Text>
      </Box>
    </Box>
  );
}
