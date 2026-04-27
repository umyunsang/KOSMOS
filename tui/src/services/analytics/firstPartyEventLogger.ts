// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration · Epic #2077 surface preservation.
// Research use — adapted from Claude Code 2.1.88 src/services/analytics/firstPartyEventLogger.ts
// Anthropic's first-party telemetry path exfiltrated typed logs to claude.ai;
// KOSMOS Migration Tree § L1-A.A7 enforces zero external egress, so both
// initialise and reinitialise paths are silent. Local OTEL (Spec 028) handles
// observability through the local OTLP collector + Langfuse.

export function initialize1PEventLogging(): void {
  return
}

export function reinitialize1PEventLoggingIfConfigChanged(): void {
  return
}
