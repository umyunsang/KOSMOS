// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T027
// PermissionLayerHeader — renders the layer-colored glyph badge (FR-016).
//
// Source: docs/wireframes/ui-c-permission.mjs § C.1 (LayerBadge)
// CC reference: .references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionRequestTitle.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: consumes LAYER_VISUAL from schemas/ui-l2/permission.ts
//   (green ⓵ / orange ⓶ / red ⓷ as per FR-016 + migration tree C.1).

import React from 'react'
import { Box, Text } from 'ink'
import {
  LAYER_VISUAL,
  type PermissionLayerT,
} from '../../schemas/ui-l2/permission.js'
import { useUiL2I18n } from '../../i18n/uiL2.js'

// Layer-specific hex colors (from ui-c-permission.mjs wireframe, frozen).
const LAYER_HEX: Record<PermissionLayerT, string> = {
  1: '#34d399', // green
  2: '#fb923c', // orange
  3: '#f87171', // red
}

export interface PermissionLayerHeaderProps {
  layer: PermissionLayerT
  toolName: string
}

/**
 * Renders the permission modal header with layer color and glyph.
 *
 * Layout (matches ui-c-permission.mjs PermissionModal header):
 *   ⓵/⓶/⓷ <layer-label> · <tool-name>
 */
export function PermissionLayerHeader({
  layer,
  toolName,
}: PermissionLayerHeaderProps): React.ReactElement {
  const i18n = useUiL2I18n()
  const visual = LAYER_VISUAL[layer]
  const color = LAYER_HEX[layer]
  const layerLabel = i18n.permissionLayer(layer)

  return (
    <Box flexDirection="row" gap={1} aria-label={visual.ariaLabel}>
      <Text color={color} bold>
        {visual.glyph}
      </Text>
      <Text bold>{layerLabel}</Text>
      <Text dimColor>·</Text>
      <Text>{toolName}</Text>
    </Box>
  )
}
