// [P0 reconstructed · Pass 3 v2 · agent-verified · SSH session factory]
// Reference: code.claude.com/docs/en/remote-control + full consumer surface
// in hooks/useSSHSession.ts (lines 72, 125, 184, 186, 206, 210, 211, 227).
//
// `claude ssh <host>` spawns a child CLI over an SSH tunnel. Upstream CC
// gates the whole SSH path behind `feature('SSH_REMOTE')` which is false
// in KOSMOS, so this file declares the types that REPL/useSSHSession need
// without running the actual SSH transport. Agent-reported v1 was missing
// createManager/proc/proxy/getStderrTail — added here for type safety.

// KOSMOS-1633 P1+P2 / KOSMOS-1978 T011 — utils/teleport/ deleted; stub.
type RemoteMessageContent = string | Array<{ type: string; [key: string]: unknown }>
import type { SSHSessionManager } from './SSHSessionManager.js'

/** ChildProcess-like handle surfaced by the SSH subprocess. */
export interface SSHChildProcessHandle {
  exitCode: number | null
  signalCode: string | null
}

/** Tunnel/proxy lifecycle control surfaced by the SSH transport. */
export interface SSHProxyHandle {
  stop(): void
}

/** Callbacks registered when building a session manager. */
export interface SSHSessionManagerCallbacks {
  onMessage: (msg: unknown) => void
  onPermissionRequest: (req: unknown, requestId: string) => void
  onConnected: () => void
  onReconnecting: (attempt: number, max: number) => void
  onDisconnected: () => void
  onError: (err: Error) => void
}

/** Minimal handle for an SSH-backed remote session. */
export interface SSHSession {
  /** SSH target string (`user@host` or host alias). */
  host: string
  /** Optional working directory on the remote side. */
  cwd?: string
  /** Permission mode to request on the remote CLI. */
  permissionMode?: string
  /** Whether `--dangerously-skip-permissions` should be forwarded. */
  dangerouslySkipPermissions: boolean
  /** Session-scoped identifier. */
  sessionId: string
  /** Open connection flag — set true once the handshake completes. */
  isConnected: boolean
  /** ChildProcess-like handle for the SSH subprocess. Used by REPL to detect exit. */
  proc: SSHChildProcessHandle
  /** Proxy/tunnel lifecycle controller. */
  proxy: SSHProxyHandle
  /** Tail of stderr from the SSH subprocess (for error dialogs). */
  getStderrTail(): string
  /** Build a manager bound to this session. */
  createManager(callbacks: SSHSessionManagerCallbacks): SSHSessionManager
}

export interface CreateSSHSessionOptions {
  host: string
  cwd?: string
  permissionMode?: string
  dangerouslySkipPermissions?: boolean
  /** CLI args to forward to the remote CLI on first spawn. */
  extraCliArgs?: string[]
}

/**
 * Create an SSH session handle. In KOSMOS this is a no-op factory that
 * returns a disconnected handle — actual transport wiring is deferred to
 * Epic #1633 (SSH_REMOTE dead code decision).
 */
export function createSSHSession(opts: CreateSSHSessionOptions): SSHSession {
  // Lazily import the manager class to avoid circular type resolution
  // when consumers destructure from both modules.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { SSHSessionManager: ManagerCtor } = require('./SSHSessionManager.js') as typeof import('./SSHSessionManager.js')

  const session: SSHSession = {
    host: opts.host,
    cwd: opts.cwd,
    permissionMode: opts.permissionMode,
    dangerouslySkipPermissions: opts.dangerouslySkipPermissions ?? false,
    sessionId: `ssh-${Date.now().toString(36)}`,
    isConnected: false,
    proc: { exitCode: null, signalCode: null },
    proxy: {
      stop() {
        /* [P0 neutralized] actual tunnel stop happens in Epic #1633 */
      },
    },
    getStderrTail: () => '',
    createManager: (callbacks) => new ManagerCtor(session, callbacks),
  }
  return session
}

/** Type guard for SSHSession. */
export function isSSHSession(value: unknown): value is SSHSession {
  return (
    typeof value === 'object' &&
    value !== null &&
    'host' in value &&
    'sessionId' in value &&
    'proc' in value
  )
}

export type { RemoteMessageContent }
