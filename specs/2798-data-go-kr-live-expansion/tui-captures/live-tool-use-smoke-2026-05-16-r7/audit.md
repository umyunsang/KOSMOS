# TUI Real-Use Audit

Overall: **pass**

## capture_completeness: pass
Capture contains final state and intermediate artifacts.

- `frames=173`
- `snapshots=5`

## utf8_replacement_character: pass
No UTF-8 replacement characters were found in captured text.

## backend_log_health: warn
backend.log is missing; backend exception health could not be audited.

## agentic_chain_order: pass
Expected tool chain was visible in chronological captures.

- `find\(mfds_easy_drug_info_lookup\)@0:final.raw.txt`
- `collection@0:final.raw.txt`
- `타이레놀@0:final.raw.txt`

## submit_ledger_evidence: pass
No submit adapter ledger evidence is required for this scenario.

## recoverable_error_loop: pass
No recoverable invalid-parameter error was visible.

## visible_abnormal_flow: pass
No audited avoidable tool-selection recovery artifact was visible.

## cc_error_rendering: pass
No tool error was visible in this capture.

## expanded_tool_trace: pass
Expanded tool trace was not required for this run.

## submit_rejected_status: pass
No rejected submit status was visible.

## raw_protocol_leak: pass
No raw IPC frame leak was detected in captured text.

## require_regex: pass
Required regex matched: mfds_easy_drug_info_lookup

## require_regex: pass
Required regex matched: collection\s*—\s*7\s*results|collection.*7.*results

## require_regex: pass
Required regex matched: 타이레놀|아세트아미노펜|acetaminophen

## forbid_regex: pass
Forbidden regex absent: 신원 확인 권한 요청|check\(|mock_verify|Traceback|ValidationError|Unknown tool|serviceKey|UMMAYA_FRIENDLI|UMMAYA_DATA|flp_|7e0a
