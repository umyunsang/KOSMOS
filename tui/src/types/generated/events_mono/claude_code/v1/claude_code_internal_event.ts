// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — protobuf events_mono stub.
//
// CC's BigQuery exporter consumes generated protobuf classes for
// 1P event logging. KOSMOS does not run the BigQuery exporter
// (we use Spec 028 OTLP collector → local Langfuse), so this stub
// only needs to satisfy the static type signature; the real consumer
// (`firstPartyEventLoggingExporter.ts`) never instantiates these
// classes in KOSMOS deployments.

export class ClaudeCodeInternalEvent {
  static fromJSON(_object: unknown): ClaudeCodeInternalEvent {
    return new ClaudeCodeInternalEvent()
  }
  static encode(_message: ClaudeCodeInternalEvent): { finish(): Uint8Array } {
    return { finish: () => new Uint8Array(0) }
  }
  toJSON(): unknown {
    return {}
  }
}
