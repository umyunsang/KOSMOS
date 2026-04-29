/**
 * KOSMOS: File persistence stubs.
 * services/api/filesApi deleted (Anthropic BYOC/Cloud session API).
 * KOSMOS does not use Anthropic session ingress — all persistence uses
 * the KOSMOS memdir (~/.kosmos/memdir/) layer from Spec 027.
 */

import type {
  FilesPersistedEventData,
  TurnStartTime,
} from './types.js'

export async function runFilePersistence(
  _turnStartTime: TurnStartTime,
  _signal?: AbortSignal,
): Promise<FilesPersistedEventData | null> {
  return null
}

export async function executeFilePersistence(
  _turnStartTime: TurnStartTime,
  _signal: AbortSignal,
  _onResult: (result: FilesPersistedEventData) => void,
): Promise<void> {}

export function isFilePersistenceEnabled(): boolean {
  return false
}
