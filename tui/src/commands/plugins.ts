// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T066 /plugins command (FR-031, US5).
// Spec 1979 T023 — replaced env-var stub with IPC round-trip via plugin_op_request:list.
//
// Opens the PluginBrowser. Emits kosmos.ui.surface=plugins (FR-037).
// Round-trips a plugin_op_request:list frame to the backend dispatcher
// (src/kosmos/ipc/plugin_op_dispatcher.py:handle_list) which responds with
// a payload_start + payload_delta + payload_end + plugin_op_complete
// quadruplet correlated by correlation_id. The payload_delta carries a
// JSON-encoded {entries: PluginListEntry[]} body that maps onto the
// PluginEntry shape rendered by PluginBrowser.tsx.

import { emitSurfaceActivation } from '../observability/surface.js';
import {
  getKosmosBridgeSessionId,
  getOrCreateKosmosBridge,
} from '../ipc/bridgeSingleton.js';
import type { PluginEntry } from '../components/plugins/PluginBrowser.js';
import type { IPCFrame } from '../ipc/frames.generated.js';

// ---------------------------------------------------------------------------
// Result type
// ---------------------------------------------------------------------------

export type PluginsCommandResult = {
  /** Current plugin registry snapshot */
  plugins: PluginEntry[];
  /** When set, an IPC round-trip error prevented populating the list. */
  error?: string;
};

// ---------------------------------------------------------------------------
// PluginListEntry — backend payload shape (mirrors plugin_op_dispatcher
// _build_list_payload). Defined here to avoid a runtime import of a Python
// schema; kept in sync with src/kosmos/ipc/plugin_op_dispatcher.py § list.
// ---------------------------------------------------------------------------

type PluginListEntry = {
  plugin_id: string;
  name: string;
  version: string;
  tier: 'live' | 'mock';
  permission_layer: 1 | 2 | 3;
  processes_pii: boolean;
  trustee_org_name: string | null;
  is_active: boolean;
  install_timestamp_iso: string;
  description_ko: string;
  description_en: string;
  search_hint_ko: string;
  search_hint_en: string;
};

// 5-second timeout for the backend round-trip — list enumerates the
// in-memory ToolRegistry which is O(n) and should complete well under 1s
// even at 100+ plugins. The timeout is fail-soft: empty list with error
// note rendered in the browser.
const _LIST_ROUND_TRIP_TIMEOUT_MS = 5_000;

// ---------------------------------------------------------------------------
// Frame builder
// ---------------------------------------------------------------------------

function _now(): string {
  return new Date().toISOString();
}

function _newCorrelationId(): string {
  return crypto.randomUUID();
}

function _buildListRequestFrame(
  sessionId: string,
  correlationId: string,
): IPCFrame {
  return {
    kind: 'plugin_op',
    version: '1.0',
    session_id: sessionId,
    correlation_id: correlationId,
    ts: _now(),
    role: 'tui',
    op: 'request',
    request_op: 'list',
  } as never;
}

// ---------------------------------------------------------------------------
// Map backend PluginListEntry → TUI-side PluginEntry
// ---------------------------------------------------------------------------

function _mapToPluginEntry(b: PluginListEntry): PluginEntry {
  return {
    id: b.plugin_id,
    name: b.name,
    version: b.version,
    description_ko: b.description_ko,
    description_en: b.description_en,
    isActive: b.is_active,
    tier: b.tier,
    layer: b.permission_layer,
    trustee_org_name: b.trustee_org_name,
    install_timestamp_iso: b.install_timestamp_iso,
    search_hint_ko: b.search_hint_ko,
    search_hint_en: b.search_hint_en,
  };
}

// ---------------------------------------------------------------------------
// IPC round-trip — collect payload triplet + complete frame, parse, return.
// ---------------------------------------------------------------------------

async function _roundTripPluginList(
  correlationId: string,
): Promise<PluginEntry[]> {
  const bridge = getOrCreateKosmosBridge();
  // Concatenated payload_delta strings (Spec 032 reassembly invariant).
  let payloadBuffer = '';
  let payloadComplete = false;
  let terminalSeen = false;

  // Wrap iteration with a timeout so a hung backend never freezes the UI.
  const deadline = Date.now() + _LIST_ROUND_TRIP_TIMEOUT_MS;

  for await (const frame of bridge.frames()) {
    if (Date.now() > deadline) {
      throw new Error('plugin_op:list round-trip timed out (5s)');
    }
    // Filter by correlation_id — frames not in our turn are ignored.
    if (
      typeof frame === 'object' &&
      frame !== null &&
      'correlation_id' in frame &&
      (frame as { correlation_id?: string }).correlation_id !== correlationId
    ) {
      continue;
    }

    const f = frame as { kind?: string; payload?: string; op?: string; result?: string };

    if (f.kind === 'payload_start') {
      payloadBuffer = '';
    } else if (f.kind === 'payload_delta' && typeof f.payload === 'string') {
      payloadBuffer += f.payload;
    } else if (f.kind === 'payload_end') {
      payloadComplete = true;
    } else if (f.kind === 'plugin_op' && f.op === 'complete') {
      terminalSeen = true;
      if (f.result !== 'success') {
        throw new Error(`plugin_op:list backend returned result=${f.result}`);
      }
      // Quadruplet complete — break out of the iterator so the bridge can
      // continue serving subsequent turns.
      break;
    }

    if (terminalSeen && payloadComplete) break;
  }

  if (!payloadComplete) {
    throw new Error(
      'plugin_op:list round-trip ended without payload_end (backend protocol violation)',
    );
  }

  // Parse payload_buffer as {entries: PluginListEntry[]}.
  let parsed: { entries?: PluginListEntry[] };
  try {
    parsed = JSON.parse(payloadBuffer);
  } catch (err) {
    throw new Error(
      `plugin_op:list payload JSON parse failed: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  if (!parsed.entries || !Array.isArray(parsed.entries)) {
    throw new Error(
      'plugin_op:list payload missing required "entries" array',
    );
  }
  return parsed.entries.map(_mapToPluginEntry);
}

// ---------------------------------------------------------------------------
// Command handler — async after T023 (FR-015 + FR-016 R-6 verdict)
// ---------------------------------------------------------------------------

/**
 * Execute the /plugins command.
 *
 * Emits `kosmos.ui.surface=plugins` (FR-037) and round-trips a
 * `plugin_op_request:list` to the backend dispatcher to obtain the live
 * plugin registry snapshot. Returns a PluginEntry[] for rendering in
 * PluginBrowser.
 *
 * Errors during the round-trip (timeout, JSON parse, backend failure) are
 * surfaced via `result.error` so the browser can render a degraded state
 * rather than crashing — caller decides whether to render an empty list
 * or an error toast.
 */
export async function executePlugins(): Promise<PluginsCommandResult> {
  // FR-037: emit surface activation at command start
  emitSurfaceActivation('plugins');

  const correlationId = _newCorrelationId();
  const sessionId = getKosmosBridgeSessionId();
  const bridge = getOrCreateKosmosBridge();

  const requestFrame = _buildListRequestFrame(sessionId, correlationId);
  const sent = bridge.send(requestFrame);
  if (!sent) {
    return {
      plugins: [],
      error: 'IPC bridge unavailable (backend exited)',
    };
  }

  try {
    const plugins = await _roundTripPluginList(correlationId);
    return { plugins };
  } catch (err) {
    return {
      plugins: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
