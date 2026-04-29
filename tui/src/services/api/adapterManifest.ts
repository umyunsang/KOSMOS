// SPDX-License-Identifier: Apache-2.0
// Epic ε #2296 · T009 — Adapter manifest singleton cache (TS side).
//
// FR-015: TS-side manifest cache populated once per backend boot.
// FR-016: cache is REPLACED on each new frame (NOT merged).
// FR-019: isManifestSynced() guards cold-boot race.
//
// Contract: specs/2296-ax-mock-adapters/contracts/ipc-adapter-manifest-frame.md § 5.2

import type { AdapterManifestEntry, AdapterManifestSyncFrame } from '../../ipc/frames.generated.js'

// Re-export AdapterManifestEntry so consumers import from one place.
export type { AdapterManifestEntry }

// ---------------------------------------------------------------------------
// Internal cache type
// ---------------------------------------------------------------------------

interface AdapterManifestCache {
  /** Map from tool_id → AdapterManifestEntry for O(1) resolution. */
  entries: Map<string, AdapterManifestEntry>
  /** SHA-256 hex of the canonical JSON entries (wire verification). */
  manifestHash: string
  /** Python backend PID at boot (for OTEL cross-correlation). */
  emitterPid: number
  /** Wall-clock time when this manifest was ingested. */
  ingestedAt: Date
}

// ---------------------------------------------------------------------------
// Module-level singleton (replace-on-frame, never merged per FR-016)
// ---------------------------------------------------------------------------

let _cache: AdapterManifestCache | null = null

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Ingest a backend-emitted ``AdapterManifestSyncFrame``.
 *
 * Replaces the module-level cache wholesale (FR-016 — do NOT merge).
 * Called by the IPC frame router when it receives a frame with
 * ``kind === 'adapter_manifest_sync'``.
 */
export function ingestManifestFrame(frame: AdapterManifestSyncFrame): void {
  _cache = {
    entries: new Map(frame.entries.map((e) => [e.tool_id, e])),
    manifestHash: frame.manifest_hash,
    emitterPid: frame.emitter_pid,
    ingestedAt: new Date(),
  }
}

/**
 * Resolve an adapter by its backend-registered ``tool_id``.
 *
 * Returns ``undefined`` when the manifest has not yet been ingested (cold-boot
 * race) or when the ``tool_id`` is absent from the synced manifest.
 *
 * Callers MUST check {@link isManifestSynced} first to distinguish the
 * cold-boot race (manifest not arrived yet) from a genuine AdapterNotFound.
 */
export function resolveAdapter(tool_id: string): AdapterManifestEntry | undefined {
  return _cache?.entries.get(tool_id)
}

/**
 * Returns ``true`` when at least one manifest frame has been ingested.
 *
 * Used by primitive ``validateInput`` to enforce the cold-boot fail-closed
 * invariant (FR-019): if the manifest has not yet synced, reject the call
 * with a retry hint rather than silently returning AdapterNotFound.
 */
export function isManifestSynced(): boolean {
  return _cache !== null
}

/**
 * Clear the manifest cache.
 *
 * **FOR TESTING ONLY.** Do not call from production code.
 * Allows tests to reset the singleton between test cases.
 */
export function clearManifestCache(): void {
  _cache = null
}
