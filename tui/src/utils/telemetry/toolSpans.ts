// SPDX-License-Identifier: Apache-2.0
// KOSAX Epic #2637 — Spec 021 OTEL Tool layer wire (4-tier OTEL).
// R-6: toolExecution.ts 9 inline stubs → this KOSAX OTEL helper module.
// Attribute namespace: kosax.tool.{id,input_size_bytes,outcome,error_type,
//   duration_ms,permission_decision,user_facing_name} per OtelAttributeContract
// (specs/2637-p0-regression/data-model.md § Entity 3).
//
// KOSAX uses @opentelemetry/api tracer/logs directly (Spec 021 OTLP pipeline →
// local Langfuse collector, Spec 028). service.name = "kosax-tui" is set by
// instrumentation.ts at boot time.

import { logs, SeverityNumber } from '@opentelemetry/api-logs'
import { trace, type Span, SpanStatusCode } from '@opentelemetry/api'

const TRACER_NAME = 'kosax.tools'
const LOGGER_NAME = 'kosax.tools'

/**
 * Emit an OTEL log event with the given name and attributes.
 * Maps to CC's logOTelEvent — KOSAX uses the logs API (Spec 021 4-tier).
 */
export function logOTelEvent(eventName: string, attrs?: unknown): void {
  try {
    const logger = logs.getLogger(LOGGER_NAME)
    logger.emit({
      severityNumber: SeverityNumber.INFO,
      severityText: 'INFO',
      body: eventName,
      attributes: attrs && typeof attrs === 'object' ? (attrs as Record<string, unknown>) : {},
    })
  } catch {
    // fail-open: never throw from telemetry path
  }
}

/**
 * Add a tool content event to a span (tool output recorded as span event).
 */
export function addToolContentEvent(span: Span | null, contentAttrs: unknown): void {
  try {
    if (!span) return
    span.addEvent('tool.output', contentAttrs && typeof contentAttrs === 'object'
      ? (contentAttrs as Record<string, unknown>)
      : {})
  } catch {
    // fail-open
  }
}

/**
 * Start a top-level tool span.
 * Span name: kosax.tool.<tool_id>
 */
export function startToolSpan(name: string, attrs?: Record<string, unknown>): Span | null {
  try {
    const tracer = trace.getTracer(TRACER_NAME)
    const span = tracer.startSpan(`kosax.tool.${name}`, {
      attributes: {
        'kosax.tool.id': name,
        ...attrs,
      },
    })
    return span
  } catch {
    return null
  }
}

/**
 * End a top-level tool span, setting outcome attribute from tool result string.
 */
export function endToolSpan(span: Span | null, toolResultStr?: string): void {
  try {
    if (!span) return
    span.setAttribute('kosax.tool.outcome', toolResultStr ? 'success' : 'error')
    span.end()
  } catch {
    // fail-open
  }
}

/**
 * Start a tool execution child span (runs inside startToolSpan context).
 */
export function startToolExecutionSpan(parentSpan: Span | null, name: string): Span | null {
  try {
    const tracer = trace.getTracer(TRACER_NAME)
    const span = tracer.startSpan(`kosax.tool.execution.${name}`, {
      attributes: { 'kosax.tool.user_facing_name': name },
    })
    return span
  } catch {
    return null
  }
}

/**
 * End a tool execution span with result.
 */
export function endToolExecutionSpan(span: Span | null, result: unknown): void {
  try {
    if (!span) return
    const outcome = result ? 'success' : 'error'
    span.setAttribute('kosax.tool.outcome', outcome)
    if (outcome === 'error') {
      span.setStatus({ code: SpanStatusCode.ERROR })
    }
    span.end()
  } catch {
    // fail-open
  }
}

/**
 * Start a "blocked on user" child span (permission gate pending).
 */
export function startToolBlockedOnUserSpan(parentSpan: Span | null): Span | null {
  try {
    const tracer = trace.getTracer(TRACER_NAME)
    const span = tracer.startSpan('kosax.tool.blocked_on_user', {
      attributes: { 'kosax.tool.outcome': 'blocked_on_user' },
    })
    return span
  } catch {
    return null
  }
}

/**
 * End a "blocked on user" span with reason.
 */
export function endToolBlockedOnUserSpan(span: Span | null, reason?: string, source?: string): void {
  try {
    if (!span) return
    if (reason) span.setAttribute('kosax.tool.permission_decision', reason)
    if (source) span.setAttribute('kosax.tool.error_type', source)
    span.end()
  } catch {
    // fail-open
  }
}

/**
 * Returns false — KOSAX does not use Anthropic beta session tracing.
 * Stub mirrors CC's isBetaTracingEnabled() signature.
 */
export function isBetaTracingEnabled(): boolean {
  return false
}
