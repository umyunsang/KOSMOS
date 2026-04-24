// [P0 reconstructed · Pass 3 · Transport interface]
// Reference: implementers WebSocketTransport.ts, SSETransport.ts, HybridTransport.ts
//            in the same directory. Each `implements Transport`; the
//            interface is the common API that the CC client code uses to
//            send stdin, receive streaming events, and manage the lifecycle.
//
// This is a type-only file — no runtime behavior — so upstream implementers
// can share a nominal interface.

import type {
  StdoutMessage,
  StreamClientEvent,
} from 'src/entrypoints/sdk/controlTypes.js'

/** Lifecycle states shared across all Transport implementations. */
export type TransportState =
  | 'idle'
  | 'connecting'
  | 'reconnecting'
  | 'connected'
  | 'closing'
  | 'closed'

/**
 * Common interface implemented by WebSocketTransport, SSETransport, and
 * HybridTransport. Consumers (the REPL bridge, stream event router, etc.)
 * code against this interface and can swap transports at runtime.
 */
export interface Transport {
  /** Establish the connection. Idempotent if already connected. */
  connect(): Promise<void>

  /** Close the connection. Idempotent if already closed. */
  close(): void

  /** Send a raw data frame. */
  send(data: string): void

  /** Send a structured message (convenience over `send`). */
  write(message: StdoutMessage): Promise<void>

  /** Register a callback for inbound data frames. */
  setOnData(callback: (data: string) => void): void

  /** Register a callback fired once when the connection opens. */
  setOnConnect(callback: () => void): void

  /** Register a callback fired when the connection closes. */
  setOnClose(callback: (closeCode?: number) => void): void

  /** Optional: register a callback for structured event frames. */
  setOnEvent?(callback: (event: StreamClientEvent) => void): void

  /** Whether the underlying transport is currently connected. */
  isConnectedStatus(): boolean

  /** Whether the underlying transport is permanently closed. */
  isClosedStatus(): boolean

  /** Human-readable state label (for diagnostics / UI). */
  getStateLabel(): string
}

export type { StdoutMessage, StreamClientEvent }
