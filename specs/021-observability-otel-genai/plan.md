# Implementation Plan: Observability — OpenTelemetry GenAI + Langfuse

**Branch**: `021-observability-otel-genai` | **Date**: 2026-04-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-observability-otel-genai/spec.md`

## Summary

KOSMOS의 에이전트 루프를 **수동 OTel GenAI span authoring** 방식으로 계측하여 Langfuse v3 자체 호스팅 스택에 전송한다. 부착점은 세 군데로 고정한다: (1) `engine/query.py`의 query 진입점에 `invoke_agent` 부모 span을 만들고 `gen_ai.conversation.id=session_id`를 부착, (2) `LLMClient.generate_stream`에 `chat` 자식 span을 만들고 스트리밍 완료 시점에 입력/출력 토큰·모델·provider를 집계해 기록하며 429 retry counter를 증가, (3) `ToolExecutor.dispatch`에 `execute_tool {tool_id}` 자식 span을 만든다.

기존 `ObservabilityEventLogger`·`MetricsCollector`는 손대지 않고 **OTel을 병렬 레이어로 추가**한다. PII whitelist는 기존 `_ALLOWED_METADATA_KEYS` frozenset을 단일 진실 소스로 삼아 span 속성에도 동일 필터를 통과한 값만 전파한다. Export는 OTLP **HTTP/protobuf**만 사용(Langfuse gRPC 미수신). `OTEL_SDK_DISABLED=true`에서 no-op 경로로 빠져 전체 테스트 스위트가 통과해야 한다.

신규 외부 런타임 의존성은 정확히 3개로 제한된다: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-semantic-conventions`. auto-instrumentor 계열(`opentelemetry-instrumentation-*`, OpenLLMetry/Traceloop 등)은 FriendliAI가 pure httpx를 사용해 훅 대상이 없고 AGENTS.md 최소 의존 원칙과도 상충하므로 **영구 거부**한다.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `httpx>=0.27` (async HTTP, 기존), `pydantic>=2.13` (모델, 기존), `opentelemetry-sdk` (신규), `opentelemetry-exporter-otlp-proto-http` (신규), `opentelemetry-semantic-conventions` (신규, GenAI v1.40 experimental opt-in)
**Storage**: N/A (span 메모리 버퍼 + OTLP 전송, 로컬 Langfuse는 Docker 스택의 Postgres/ClickHouse/MinIO가 담당)
**Testing**: `pytest` + `pytest-asyncio` (기존). 신규 테스트는 `InMemorySpanExporter`(otel-sdk 내장)를 사용하여 네트워크 없이 span 구조/속성 검증.
**Target Platform**: macOS/Linux 개발환경 + Docker(로컬 Langfuse v3 스택). CI는 `OTEL_SDK_DISABLED=true` 경로.
**Project Type**: Single project (Python CLI + 모듈 라이브러리) — `src/kosmos/observability/` 아래에 OTel 레이어 확장.
**Performance Goals**: span 부가 오버헤드는 한 LLM/도구 호출당 <1ms p95 (집계·export 제외). BatchSpanProcessor는 비동기 background flush.
**Constraints**: (a) 기존 `ObservabilityEventLogger`·`MetricsCollector`·`ObservabilityEvent` API 변경 금지(하위 호환). (b) PII whitelist는 재사용, 중복 구현 금지. (c) 런타임 의존성 정확히 +3개. (d) gRPC exporter 금지.
**Scale/Scope**: 단일 프로세스·단일 에이전트 세션 단위. Phase 2 시나리오당 수십~수백 span/session 규모. 샘플링 없음(1:1).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Reference-Driven Development | 모든 설계 결정이 `docs/vision.md § Reference materials` 또는 OTel 공식 semconv에 매핑됨 (Phase 0 research.md 참조) | PASS |
| II. Fail-Closed Security (NON-NEGOTIABLE) | OTel 레이어는 기존 fail-closed 기본값 변경 없음. PII whitelist 재사용으로 속성 유출 차단. `OTEL_SDK_DISABLED` 기본 비활성은 아니나, 엔드포인트 미설정 시 no-op + 경고 로그 1회 → 관측성 장애가 애플리케이션을 깨지 않음. | PASS |
| III. Pydantic v2 Strict Typing (NON-NEGOTIABLE) | 신규 I/O 모델은 Pydantic v2. OTel SDK의 Span은 외부 객체이므로 Pydantic 요구 대상 아님(라이브러리 경계). 내부에서 노출하는 설정·이벤트 구조체만 Pydantic v2. | PASS |
| IV. Government API Compliance | 본 epic은 `data.go.kr` 호출을 추가/변경하지 않음. 관측 레이어는 기존 어댑터 호출을 감싸기만 함. CI에서 live 호출 없음. | PASS |
| V. Policy Alignment (PIPA) | 개인정보 식별자는 span 속성에 실리지 않음(whitelist 통과 값만 전파). 세션 ID는 PIPA상 개인정보 아님(랜덤 UUID). | PASS |
| VI. Deferred Work Accountability | spec.md "Scope Boundaries & Deferred Items" 섹션에 4개 `NEEDS TRACKING` 엔트리 등록됨. 자유문에 미등록 "future/phase 2+" 없음. | PASS |

**Gate result**: PASS (no violations, Complexity Tracking 불필요)

### Post-Design Re-check (after Phase 1)

Phase 1 산출물(`data-model.md`, `contracts/otel-span-contract.md`, `quickstart.md`) 작성 후 6원칙 재검증:

| Principle | Post-design 상태 | 근거 |
|---|---|---|
| I. Reference-Driven | 모든 신규 wire contract(span 이름·속성·metric)가 OTel GenAI semconv v1.40 또는 Langfuse 공식 docs에 매핑. `contracts/otel-span-contract.md § References` 참조. | PASS |
| II. Fail-Closed | `data-model.md § E5` whitelist는 단일 진실 소스. no-op 계약(`§ No-op contract`)은 네트워크 0 보장. | PASS |
| III. Pydantic v2 Strict | 신규 Pydantic 모델은 `TracingSettings` 1개(`frozen=True`, `extra="forbid"`). OTel Span은 외부 객체 경계. | PASS |
| IV. Government API | 정부 API 호출 불변. 관측 레이어는 감싸기만 함. | PASS |
| V. PIPA | `contracts § PII rule`: tool payload·API response body 부착 금지를 wire contract로 명시. | PASS |
| VI. Deferred Accountability | spec.md Deferred 4항목 그대로 유지. Phase 1에서 신규 deferral 없음. | PASS |

**Post-design gate**: PASS. Complexity Tracking 여전히 비어 있음.

## Project Structure

### Documentation (this feature)

```text
specs/021-observability-otel-genai/
├── plan.md              # This file (/speckit.plan output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── otel-span-contract.md  # Phase 1 output — span name/attribute wire contract
├── checklists/
│   └── requirements.md
└── tasks.md             # (/speckit.tasks output — not created here)
```

### Source Code (repository root)

```text
src/kosmos/observability/
├── __init__.py                 # 기존
├── events.py                   # 기존 — 손대지 않음
├── event_logger.py             # 기존 — 손대지 않음 (PII whitelist 단일 진실 소스)
├── metrics.py                  # 기존 — 손대지 않음
├── tracing.py                  # NEW — OTel TracerProvider 초기화 + no-op 분기
├── otel_bridge.py              # NEW — ObservabilityEvent → span 속성 매퍼 (whitelist 재사용)
└── semconv.py                  # NEW — GenAI 속성 상수(v1.40) 중앙화

src/kosmos/llm/client.py        # MODIFY — generate_stream 내 chat span 생성 + 429 counter
src/kosmos/tools/executor.py    # MODIFY — dispatch 내 execute_tool span 생성
src/kosmos/engine/query.py      # MODIFY — query() 진입점에 invoke_agent parent span 생성

tests/observability/
├── test_tracing_init.py        # NEW — 초기화/OTEL_SDK_DISABLED no-op
├── test_llm_chat_span.py       # NEW — InMemorySpanExporter로 chat span 속성 검증
├── test_tool_execute_span.py   # NEW — execute_tool span + 에러 상태 검증
├── test_query_parent_span.py   # NEW — invoke_agent span + 자식 계층 검증
├── test_otel_bridge_pii.py     # NEW — whitelist 필터링 재사용 검증
└── test_retry_429_counter.py   # NEW — 429 발생 시 counter 증가 검증

docker-compose.dev.yml          # NEW — Langfuse v3 + Postgres + Redis + ClickHouse + MinIO
.env.example                    # MODIFY — OTEL_* 변수 블록 추가
pyproject.toml                  # MODIFY — 3개 OTel 의존 추가
```

**Structure Decision**: 단일 프로젝트 구조. 신규 모듈 3개(`tracing.py`, `otel_bridge.py`, `semconv.py`)를 기존 `src/kosmos/observability/` 패키지에 추가하여 **단일 진입점**(`src/kosmos/observability/__init__.py`)을 통해 노출. 기존 `event_logger.py`·`metrics.py`는 수정하지 않는다. 부착점 3개(`llm/client.py`, `tools/executor.py`, `engine/query.py`)에는 *optional* 의존(tracer 주입식)으로 추가하여, tracer가 없을 때 기존 동작 변화 없음.

## Complexity Tracking

> No violations. Table intentionally empty.
