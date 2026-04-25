// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T066 /plugins command (FR-031, US5).
//
// Opens the PluginBrowser.  Emits kosmos.ui.surface=plugins (FR-037).

import { emitSurfaceActivation } from '../observability/surface.js';
import type { PluginEntry } from '../components/plugins/PluginBrowser.js';

// ---------------------------------------------------------------------------
// Result type
// ---------------------------------------------------------------------------

export type PluginsCommandResult = {
  /** Current plugin registry snapshot */
  plugins: PluginEntry[];
};

// ---------------------------------------------------------------------------
// Command handler (T066)
// ---------------------------------------------------------------------------

/**
 * Execute the /plugins command.
 *
 * Emits `kosmos.ui.surface=plugins` (FR-037) and returns the current plugin
 * list for rendering in PluginBrowser.
 *
 * In the P4 MVP, the plugin registry is an in-memory list read from
 * KOSMOS_PLUGIN_REGISTRY env var (JSON array) or returned empty.
 * P5 Plugin DX will replace this with a real registry adapter.
 */
export function executePlugins(): PluginsCommandResult {
  // FR-037: emit surface activation at command start
  emitSurfaceActivation('plugins');

  let plugins: PluginEntry[] = [];

  const registryEnv = process.env['KOSMOS_PLUGIN_REGISTRY'];
  if (registryEnv) {
    try {
      const raw = JSON.parse(registryEnv);
      if (Array.isArray(raw)) {
        plugins = raw as PluginEntry[];
      }
    } catch {
      // Malformed env — return empty list; P5 will provide real registry
    }
  }

  return { plugins };
}
