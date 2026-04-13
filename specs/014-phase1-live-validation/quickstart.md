# Quickstart: Phase 1 Final Validation & Stabilization (Live)

## Prerequisites

1. Python 3.12+ with `uv` installed
2. Valid API credentials:
   - `KOSMOS_FRIENDLI_TOKEN` — FriendliAI Serverless API token
   - `KOSMOS_DATA_GO_KR_API_KEY` — data.go.kr public data portal key
   - `KOSMOS_KOROAD_API_KEY` — KOROAD open data portal key

## Setup

```bash
# 1. Clone and checkout branch
git checkout 014-phase1-live-validation

# 2. Install dependencies
uv sync

# 3. Set environment variables
cp .env.example .env
# Edit .env with your real API keys
```

## Verify Precondition: Existing Tests Pass

```bash
# All mock-based tests must pass before live validation
uv run pytest --tb=long -v
```

## Run Live Tests

```bash
# Run all live tests (requires real API credentials)
uv run pytest -m live -v --tb=long

# Run specific adapter live tests
uv run pytest tests/live/test_live_koroad.py -v
uv run pytest tests/live/test_live_kma.py -v
uv run pytest tests/live/test_live_llm.py -v
uv run pytest tests/live/test_live_composite.py -v

# Run live E2E pipeline test
uv run pytest tests/live/test_live_e2e.py -v
```

## Manual CLI Validation

```bash
# Start KOSMOS CLI
uv run kosmos

# Scenario 1 happy path:
# > 내일 부산에서 서울 가는데, 안전한 경로 추천해줘

# Multi-turn follow-up:
# > 대전-천안 구간 사고 이력 더 자세히 알려줘

# Error handling: press Ctrl+C during streaming to test cancellation
```

## Run Full Suite (Mock + Live)

```bash
# Complete validation
uv run pytest -v --tb=long
```

## Key Files

| File | Purpose |
|------|---------|
| `tests/live/conftest.py` | Shared live test fixtures and credential validation |
| `tests/live/test_live_*.py` | Individual adapter and E2E live tests |
| `tests/conftest.py` | Root conftest — skips live tests unless `-m live` |
| `src/kosmos/engine/engine.py` | PermissionPipeline wiring fix |
| `.env.example` | Environment variable reference (corrected naming) |
