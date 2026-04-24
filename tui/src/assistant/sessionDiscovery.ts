// [P0 reconstructed · Pass 3 · KAIROS assistant session discovery]
// Reference: claude-reviews-claude §09 session-persistence +
//            platform.claude.com/docs/en/agent-sdk/sessions +
//            DeepWiki claude-agent-sdk-python §6.1 Session Management.
//
// Discovers persisted assistant sessions (KAIROS mode) from the standard CC
// session storage location `~/.claude/projects/<sanitized-cwd>/*.jsonl`.
// Each JSONL file is a session; entries with `type === 'agent-name'` tag a
// session as assistant-backed. This module enumerates those files with stat-
// mtime sorting (no full content read) and exposes a picker-ready result.
//
// Upstream CC gates this behind `feature('KAIROS')`; in KOSMOS we leave it
// functional so that (a) the types are honest, (b) if KAIROS is ever
// enabled, the picker works.

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

/** One persisted assistant session, as the chooser UI expects. */
export interface AssistantSession {
  /** The JSONL filename stem (session ID). */
  sessionId: string
  /** Human-readable title — from `custom-title` or `ai-title` entry. */
  title: string | null
  /** ISO timestamp of last write (mtime). */
  lastActivityIso: string
  /** Absolute path to the JSONL file. */
  filePath: string
  /** Number of assistant/user turns — best-effort line count. */
  approxTurnCount: number
  /** Agent color tag, if one was stored with the session. */
  agentColor: string | null
}

/**
 * Sanitize a filesystem path the same way CC does for project dirs:
 * replace every non-alphanumeric character with `-`. CC additionally
 * hashes for overflow when paths exceed 200 chars; not required for
 * read-only discovery here.
 */
function sanitizeProjectDir(cwd: string): string {
  return cwd.replace(/[^A-Za-z0-9]/g, '-')
}

/** Absolute path to the per-project session directory. */
export function getProjectSessionDir(cwd: string = process.cwd()): string {
  return join(homedir(), '.claude', 'projects', sanitizeProjectDir(cwd))
}

/**
 * Discover all assistant-eligible sessions for the given working directory.
 * Returns them sorted by last activity (most recent first).
 * Safe on first run: if the projects dir doesn't exist, returns [].
 */
export function discoverAssistantSessions(
  cwd: string = process.cwd(),
): AssistantSession[] {
  const dir = getProjectSessionDir(cwd)
  if (!existsSync(dir)) return []

  let files: string[]
  try {
    files = readdirSync(dir).filter((f) => f.endsWith('.jsonl'))
  } catch {
    return []
  }

  const sessions: AssistantSession[] = []
  for (const file of files) {
    const filePath = join(dir, file)
    let st
    try {
      st = statSync(filePath)
    } catch {
      continue
    }

    const sessionId = file.replace(/\.jsonl$/, '')
    let title: string | null = null
    let agentColor: string | null = null
    let turnCount = 0
    let hasAgentMarker = false

    // Lightweight scan — read file header only (first 64KB) for metadata.
    // Full scan would be O(file-size) × O(N sessions); CC caps at 64KB which
    // hits most metadata entries that sit near the top.
    try {
      const raw = readFileSync(filePath, 'utf8').slice(0, 64 * 1024)
      for (const line of raw.split('\n')) {
        if (!line) continue
        let entry: Record<string, unknown>
        try {
          entry = JSON.parse(line) as Record<string, unknown>
        } catch {
          continue
        }
        const type = entry.type as string | undefined
        if (type === 'agent-name' || type === 'agent-color') {
          hasAgentMarker = true
          if (type === 'agent-color' && typeof entry.value === 'string') {
            agentColor = entry.value
          }
        } else if (type === 'custom-title' && typeof entry.value === 'string') {
          title = entry.value
        } else if (
          !title &&
          type === 'ai-title' &&
          typeof entry.value === 'string'
        ) {
          title = entry.value
        } else if (type === 'user' || type === 'assistant') {
          turnCount++
        }
      }
    } catch {
      continue
    }

    if (!hasAgentMarker) continue

    sessions.push({
      sessionId,
      title,
      lastActivityIso: st.mtime.toISOString(),
      filePath,
      approxTurnCount: turnCount,
      agentColor,
    })
  }

  sessions.sort(
    (a, b) =>
      new Date(b.lastActivityIso).getTime() -
      new Date(a.lastActivityIso).getTime(),
  )
  return sessions
}

/** Convenience: find one session by ID across all projects. */
export function findAssistantSessionById(
  sessionId: string,
  cwd: string = process.cwd(),
): AssistantSession | null {
  return (
    discoverAssistantSessions(cwd).find((s) => s.sessionId === sessionId) ??
    null
  )
}
