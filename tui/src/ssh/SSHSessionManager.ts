// [P0 reconstructed · Pass 3 v2 · agent-verified · SSH session manager]
// Reference: full consumer surface in hooks/useSSHSession.ts (lines 125,
// 134, 144, 206, 210, 227) + CC Remote Control docs.
//
// Wraps an SSHSession with a message-pump abstraction the REPL uses to
// route user input to a remote CLI and collect responses. Upstream CC
// implements this over a JSONL stdio channel tunneled via SSH; in KOSMOS
// it stays a disconnected shell until Epic #1633 decides whether to port
// or delete the SSH feature.

// KOSMOS-1633 P1+P2 / KOSMOS-1978 T011 — utils/teleport/ deleted; stub.
type RemoteMessageContent = string | Array<{ type: string; [key: string]: unknown }>
import type {
  SSHSession,
  SSHSessionManagerCallbacks,
} from './createSSHSession.js'

/** Lifecycle manager for a single SSH-backed session. */
export class SSHSessionManager {
  private session: SSHSession
  private callbacks: SSHSessionManagerCallbacks | undefined
  private disposed = false

  constructor(session: SSHSession, callbacks?: SSHSessionManagerCallbacks) {
    this.session = session
    this.callbacks = callbacks
  }

  /** Whether the remote CLI has acked the handshake. */
  isInitialized(): boolean {
    return this.session.isConnected
  }

  /**
   * Start the SSH connection. In KOSMOS this is a no-op — the underlying
   * transport is deferred to Epic #1633. Returns immediately.
   */
  connect(): void {
    if (this.disposed) return
    // [P0 neutralized] actual SSH handshake happens in Epic #1633
  }

  /**
   * Send a user message to the remote CLI. Returns true if the send was
   * queued, false if the session is disposed or not yet connected.
   */
  async sendMessage(_content: RemoteMessageContent): Promise<boolean> {
    if (this.disposed) return false
    if (!this.session.isConnected) return false
    return true
  }

  /** Abort the in-flight request without closing the session. */
  cancelRequest(): void {
    /* [P0 neutralized] cancel frame sent in Epic #1633 */
  }

  /** Send a SIGINT-like interrupt frame to the remote CLI. */
  sendInterrupt(): void {
    /* [P0 neutralized] interrupt frame sent in Epic #1633 */
  }

  /**
   * Respond to a remote permission request. `requestId` identifies the
   * pending prompt; `decision` carries the user's choice (accept/deny/etc).
   */
  respondToPermissionRequest(_requestId: string, _decision: unknown): void {
    /* [P0 neutralized] permission reply sent in Epic #1633 */
  }

  /** Close the SSH connection and release resources. */
  disconnect(): void {
    if (this.disposed) return
    this.disposed = true
    this.session.isConnected = false
    this.callbacks = undefined
  }

  /** Internal: called by the transport when the remote init ack arrives. */
  _handleInitAck(): void {
    if (this.disposed) return
    if (!this.session.isConnected) {
      this.session.isConnected = true
      this.callbacks?.onConnected()
    }
  }

  /** Internal: called by the transport for each inbound message. */
  _handleRemoteMessage(msg: unknown): void {
    if (this.disposed) return
    this.callbacks?.onMessage(msg)
  }
}
