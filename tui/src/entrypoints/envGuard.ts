// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 T011 fail-closed env guard.
//
// Enforces FR-004 edge case: TUI MUST refuse to start without a FriendliAI
// credential environment variable, emitting a bilingual error envelope and
// exiting with status 1 before any IPC bridge or Python backend handshake
// is attempted. Under no circumstance does the TUI look up Anthropic
// credentials (Keychain, OAuth, apiKeyHelper) — those code paths are
// deleted in Wave B / Wave C.
//
// Intentionally Node/Bun-stdlib only: no imports from ipc/, bridge/, or
// LLM layers — this runs *before* anything else in main().

export const ENV_GUARD_MESSAGE =
  'FRIENDLI_API_KEY 환경변수가 필요합니다 / FRIENDLI_API_KEY environment variable required'

/**
 * Check whether a valid FriendliAI credential is present in the process
 * environment. Both names are accepted for backwards compatibility with
 * different bootstrap scripts:
 *   - FRIENDLI_API_KEY (canonical, documented in quickstart.md)
 *   - KOSMOS_FRIENDLI_TOKEN (equivalent; populated by the Python backend
 *     config layer at src/kosmos/llm/config.py:LLMClientConfig.token)
 */
export function hasFriendliCredential(
  env: Record<string, string | undefined> = process.env,
): boolean {
  const friendli = env.FRIENDLI_API_KEY
  const kosmos = env.KOSMOS_FRIENDLI_TOKEN
  return Boolean(
    (friendli && friendli.trim().length > 0) ||
      (kosmos && kosmos.trim().length > 0),
  )
}

/**
 * Enforces the fail-closed credential gate at boot. If no credential is
 * present, writes the bilingual error message to stderr and exits the
 * process with status 1. Otherwise, returns void and boot continues.
 *
 * The second argument is injection seams for tests — production callers
 * should invoke with no arguments so the real `process.env`, `console.error`,
 * and `process.exit` are used.
 */
export function enforceFriendliCredential(
  env: Record<string, string | undefined> = process.env,
  hooks: {
    writeError?: (msg: string) => void
    exit?: (code: number) => never
  } = {},
): void {
  if (hasFriendliCredential(env)) {
    return
  }

  const writeError = hooks.writeError ?? ((msg: string) => console.error(msg))
  const exit =
    hooks.exit ??
    ((code: number) => {
      process.exit(code)
    })

  writeError(ENV_GUARD_MESSAGE)
  exit(1) as never
}
