# TUI Real-Use Audit

Overall: **pass**

## capture_completeness: pass
Capture contains final state and intermediate artifacts.

- `frames=9`
- `snapshots=3`

## agentic_chain_order: pass
No explicit chain expectation configured.

## recoverable_error_loop: pass
No recoverable invalid-parameter error was visible.

## cc_error_rendering: pass
No tool error was visible in this capture.

## expanded_tool_trace: pass
Expanded tool trace was not required for this run.

## raw_protocol_leak: pass
No raw IPC frame leak was detected in captured text.

## forbid_regex: pass
Forbidden regex absent: \{"version":"1\.0"

## forbid_regex: pass
Forbidden regex absent: "correlation_id"
