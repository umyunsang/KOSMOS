# KOSMOS Research

Academic research artifacts for KOSMOS. This directory supports conference and journal submissions alongside the main implementation.

## Directory structure

```
research/
├── papers/              # Paper drafts (LaTeX or Markdown)
│   ├── ksc2026/         # KSC 2026 submission
│   └── journal/         # KCI journal submission
├── experiments/         # Evaluation scripts and results
│   ├── scenarios/       # Citizen request test scenarios (JSON)
│   ├── baselines/       # Baseline system implementations
│   └── results/         # Raw experiment output (CSV/JSON)
├── figures/             # Charts, diagrams, architecture figures
├── data/                # Evaluation datasets (no PII, no API keys)
└── README.md
```

## Paper targets

| Venue | Type | Deadline (est.) | Status |
|-------|------|-----------------|--------|
| KSC 2026 | Full paper (student track) | Aug-Sep 2026 | Planned |
| KCC 2027 | Demo paper | Mar 2027 | Planned |
| KIPS Journal | KCI journal article | Rolling | Planned |

## Evaluation plan

### E1: Task completion rate
- 50 citizen request scenarios across 5+ ministries
- Metric: correct resolution rate (%) vs. baselines

### E2: Tool discovery accuracy
- Precision/recall of API selection given citizen query
- Test set: labeled (query → correct API set) pairs

### E3: Latency and cost
- Prompt cache hit rate, token usage, API call count per scenario
- Compare: cache-partitioned vs. naive (all tools in prompt)

### E4: User study (5-10 participants)
- Task: 5 cross-ministry scenarios, KOSMOS vs. data.go.kr portal
- Metrics: task completion time, success rate, SUS score

### E5: Ablation study
- Remove one layer at a time, measure degradation

## Rules

- No PII or real citizen data in this directory
- No API keys or secrets
- Experiment scripts must be reproducible (`uv run`)
- Raw results committed; derived figures regenerated from scripts
