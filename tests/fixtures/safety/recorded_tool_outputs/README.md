# Recorded Tool Outputs — SC-004 500-Turn Clean Corpus

**Purpose**: Source of truth for the false-positive measurement required by SC-004 (spec.md § Success Criteria).

## What lives here

500 recorded tool outputs from real KOSMOS tool invocations (`koroad_*`, `kma_forecast_fetch`, `hira_hospital_search`, `nmc_emergency_search`). These are **clean** outputs — no PII, no injection attempts — and they represent the traffic the Layer C detector must **not** block.

## How it is used

- T025 (`/specs/026-safety-rails/tasks.md`): measure detector false-positive rate on the 500-turn corpus; target is **zero**.
- T041 (final polish): re-run the measurement and record the result in the PR-B body.

## Format

Each file is a JSON document with:

```json
{
  "tool": "<tool_name>",
  "timestamp": "<ISO-8601>",
  "output": "<raw adapter output string>"
}
```

## Collection

Outputs are collected from recorded fixtures under `tests/fixtures/` already used by tool adapter tests. This directory aggregates them into a single corpus so the SC-004 audit is reproducible.

## Out of scope

- Live-API calls (never run against data.go.kr in CI — AGENTS.md hard rule).
- PII-carrying outputs (those belong in `tests/fixtures/safety/pii_samples.json`).
- Injection-carrying outputs (those belong in `tests/fixtures/safety/injection_samples.json`).
