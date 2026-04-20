// SPDX-License-Identifier: Apache-2.0
// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port)
//
// Filesystem read/write helpers for the memdir USER tier.  The TUI writes
// consent + ministry-scope records directly to `~/.kosmos/memdir/user/...`
// using the same atomic-write pattern as `src/kosmos/memdir/*.py`: tmp file
// + fsync + rename.  Reading scans descending filenames and returns the
// first Zod-validating record.
//
// Direct-filesystem persistence keeps Epic H self-contained — no new IPC
// frame type is required.  Python reads the same directory via
// `latest_consent()` / `latest_scope()`; both producers share POSIX fsync
// ordering for durability.

import {
  closeSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readdirSync,
  readFileSync,
  renameSync,
  writeSync,
} from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import { PIPAConsentRecordSchema, type PIPAConsentRecord } from './consent'
import {
  MinistryScopeAcknowledgmentSchema,
  type MinistryScopeAcknowledgment,
} from './ministry-scope'

export const DEFAULT_MEMDIR_ROOT = join(homedir(), '.kosmos', 'memdir')

// ---------------------------------------------------------------------------
// Common: atomic write
// ---------------------------------------------------------------------------

/** Escape the `:` characters in an ISO timestamp so it is a safe filename. */
function formatIsoForFilename(isoUtc: string): string {
  // Input shape: 2026-04-20T14:32:05.123Z  →  2026-04-20T14-32-05Z
  const noMillis = isoUtc.replace(/\.\d+Z$/, 'Z')
  return noMillis.replace(/:/g, '-')
}

function atomicWriteJson(path: string, bodyText: string): void {
  const parent = dirname(path)
  mkdirSync(parent, { recursive: true, mode: 0o700 })
  const tmpPath = `${path}.tmp`
  const fd = openSync(tmpPath, 'w', 0o600)
  try {
    writeSync(fd, bodyText)
    fsyncSync(fd)
  } finally {
    closeSync(fd)
  }
  renameSync(tmpPath, path)
}

// ---------------------------------------------------------------------------
// Consent records
// ---------------------------------------------------------------------------

export function consentDir(root: string = DEFAULT_MEMDIR_ROOT): string {
  return join(root, 'user', 'consent')
}

export function writeConsentRecord(
  record: PIPAConsentRecord,
  root: string = DEFAULT_MEMDIR_ROOT,
): string {
  const parsed = PIPAConsentRecordSchema.parse(record)
  const ts = formatIsoForFilename(parsed.timestamp)
  const filename = `${ts}-${parsed.session_id}.json`
  const fullPath = join(consentDir(root), filename)
  atomicWriteJson(fullPath, JSON.stringify(parsed))
  return fullPath
}

export function latestConsentRecord(
  root: string = DEFAULT_MEMDIR_ROOT,
): PIPAConsentRecord | null {
  return latestRecord(consentDir(root), (body) =>
    PIPAConsentRecordSchema.safeParse(JSON.parse(body)),
  )
}

// ---------------------------------------------------------------------------
// Ministry-scope records
// ---------------------------------------------------------------------------

export function scopeDir(root: string = DEFAULT_MEMDIR_ROOT): string {
  return join(root, 'user', 'ministry-scope')
}

export function writeScopeRecord(
  record: MinistryScopeAcknowledgment,
  root: string = DEFAULT_MEMDIR_ROOT,
): string {
  const parsed = MinistryScopeAcknowledgmentSchema.parse(record)
  const ts = formatIsoForFilename(parsed.timestamp)
  const filename = `${ts}-${parsed.session_id}.json`
  const fullPath = join(scopeDir(root), filename)
  atomicWriteJson(fullPath, JSON.stringify(parsed))
  return fullPath
}

export function latestScopeRecord(
  root: string = DEFAULT_MEMDIR_ROOT,
): MinistryScopeAcknowledgment | null {
  return latestRecord(scopeDir(root), (body) =>
    MinistryScopeAcknowledgmentSchema.safeParse(JSON.parse(body)),
  )
}

// ---------------------------------------------------------------------------
// Internal: shared "latest record in dir" scanner
// ---------------------------------------------------------------------------

type ZodSafeParse<T> =
  | { success: true; data: T }
  | { success: false; error: unknown }

function latestRecord<T>(
  dir: string,
  parse: (body: string) => ZodSafeParse<T>,
): T | null {
  let entries: string[]
  try {
    entries = readdirSync(dir)
  } catch {
    // Dir missing / permission-denied / broken symlink — fail-closed.
    return null
  }
  const jsons = entries.filter((name) => name.endsWith('.json')).sort().reverse()
  for (const name of jsons) {
    try {
      const body = readFileSync(join(dir, name), 'utf8')
      const result = parse(body)
      if (result.success) return result.data
    } catch {
      // Skip unreadable or non-JSON records, keep walking back.
      continue
    }
  }
  return null
}
