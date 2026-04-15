# Phase 1 Data Model — Observability (OTel GenAI + Langfuse)

**Feature**: `021-observability-otel-genai`
**Date**: 2026-04-15

본 문서는 span·속성·메트릭의 논리 데이터 모델을 정의한다. 외부 관측 계약(wire contract)은 `contracts/otel-span-contract.md`에 있고, 본 문서는 내부 Python 표현(Pydantic v2 + OTel API)과 **값의 의미**에 집중한다.

## Entities overview

| Entity | Kind | Owner module | Lifetime |
|---|---|---|---|
| `TracingSettings` | Pydantic v2 model | `src/kosmos/observability/tracing.py` | 프로세스 부팅 시 1회 생성 |
| `InvokeAgentSpan` | OTel Span (논리적 분류) | `src/kosmos/engine/query.py` | query 호출 당 1개 (parent) |
| `ChatSpan` | OTel Span | `src/kosmos/llm/client.py` | LLM 호출 당 1개 |
| `ExecuteToolSpan` | OTel Span | `src/kosmos/tools/executor.py` | 도구 실행 당 1개 |
| `FilteredAttributes` | `dict[str, AttributeValue]` | `src/kosmos/observability/otel_bridge.py` | span.set_attributes 입력 |
| `RateLimitRetryCounter` | Counter metric (기존 `MetricsCollector` 확장) | `src/kosmos/observability/metrics.py` 소비자 | 프로세스 lifetime |

> 신규 I/O Pydantic 모델은 `TracingSettings` 1개뿐이다. Span은 OTel SDK가 관리하는 외부 객체이므로 Pydantic 대상이 아니다(Principle III 경계).

## E1. TracingSettings

부팅 시 환경변수를 읽어 tracing 동작을 결정한다.

```python
# src/kosmos/observability/tracing.py
from pydantic import BaseModel, ConfigDict, Field

class TracingSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="False면 NoOpTracerProvider 사용. OTEL_SDK_DISABLED=true 시 False."
    )
    endpoint: str | None = Field(
        default=None,
        description="OTLP HTTP endpoint. None이면 exporter 미구성 → no-op."
    )
    protocol: str = Field(
        default="http/protobuf",
        description="OTLP 프로토콜. http/protobuf만 허용(gRPC 금지)."
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="OTLP exporter 헤더(Langfuse Basic auth 포함)."
    )
    service_name: str = Field(default="kosmos", description="OTel resource service.name.")
    semconv_opt_in: str = Field(
        default="gen_ai_latest_experimental",
        description="OTEL_SEMCONV_STABILITY_OPT_IN 값."
    )
```

**Validation rules**:
- `protocol` ∈ `{"http/protobuf"}` — 그 외 값이면 경고 로그 후 `enabled=False`로 강등.
- `endpoint`가 `None`이고 `enabled=True`인 경우: `NoOpTracerProvider` 자동 선택 + 1회 경고 로그.
- `headers` 키에 `Authorization`이 있으면 값은 로그/재노출 금지(빌트인 Pydantic 직렬화는 사용 안 함).

**State transitions**: 부팅 시 한 번 구성, 이후 immutable(`frozen=True`).

## E2. InvokeAgentSpan (parent)

Query 진입점에서 생성되는 최상위 에이전트 span.

| 속성 | 필수 | 타입 | 값 | 출처 |
|---|---|---|---|---|
| `span.name` | ✅ | str | `"invoke_agent kosmos-query"` | 상수 |
| `gen_ai.operation.name` | ✅ | str | `"invoke_agent"` | semconv 상수 |
| `gen_ai.agent.name` | ✅ | str | `"kosmos-query"` | 상수 |
| `gen_ai.conversation.id` | 조건부 | str | `QueryContext.session_context.session_id` | 런타임 |
| `gen_ai.agent.description` | ❌ | str | 생략 | — |

**Conditional rule**: `session_context is None`이면 `gen_ai.conversation.id`를 **부착하지 않는다**(속성 누락). 빈 문자열 금지.

**Status mapping**:
- 정상 종료: `Status(StatusCode.UNSET)` (OTel 권장 — success는 unset)
- 예외 전파: `Status(StatusCode.ERROR)` + `span.record_exception(exc)` + `error.type=<class>`.

**Parent-child**: 같은 async context 안에서 만들어지는 `ChatSpan`, `ExecuteToolSpan`은 OTel context propagation으로 자동 자식이 된다.

## E3. ChatSpan

LLM 호출 당 1개. 스트리밍 완료 시점에 usage/finish_reasons 집계 결과를 기록한다.

| 속성 | 필수 | 타입 | 값 / 출처 |
|---|---|---|---|
| `span.name` | ✅ | str | `"chat"` |
| `gen_ai.operation.name` | ✅ | str | `"chat"` |
| `gen_ai.provider.name` | ✅ | str | `"friendliai"` (v1.37 rename — `gen_ai.system` 금지) |
| `gen_ai.request.model` | ✅ | str | `LLMClient` 요청 모델명 |
| `gen_ai.response.model` | ✅ | str | 서버 응답 `model` 필드(없으면 request와 동일) |
| `gen_ai.usage.input_tokens` | ✅ | int | 스트림 종료 시 집계 |
| `gen_ai.usage.output_tokens` | ✅ | int | 스트림 종료 시 집계 |
| `gen_ai.response.finish_reasons` | ✅ | list[str] | `["stop"]`, `["tool_calls"]` 등 |
| `gen_ai.request.temperature` | ❌ | float | 요청에 포함된 경우만 |
| `gen_ai.request.max_tokens` | ❌ | int | 요청에 포함된 경우만 |
| `error.type` | 조건부 | str | 실패 시 `exc.__class__.__name__` |

**Streaming usage aggregation**: 청크마다 속성을 갱신하지 않는다. `LLMClient.generate_stream` 내부 누적기(`src/kosmos/llm/usage.py`)가 기존 방식대로 동작, **스트림 finalize 직후** `span.set_attributes(...)` 1회 호출로 커밋.

**Retry behavior**: 429 재시도는 span을 분기하지 않는다. 같은 `chat` span 안에서 `kosmos_llm_rate_limit_retries_total` counter가 증가한다(E6 참조).

## E4. ExecuteToolSpan

도구 실행 당 1개. `ToolExecutor.dispatch` 내부에서 생성.

| 속성 | 필수 | 타입 | 값 / 출처 |
|---|---|---|---|
| `span.name` | ✅ | str | `f"execute_tool {tool_id}"` |
| `gen_ai.operation.name` | ✅ | str | `"execute_tool"` |
| `gen_ai.tool.name` | ✅ | str | `tool_id` |
| `gen_ai.tool.type` | ✅ | str | `"function"` (KOSMOS는 전 도구가 함수형) |
| `gen_ai.tool.call.id` | ❌ | str | LLM 응답의 tool_call_id가 있으면 부착 |
| `error.type` | 조건부 | str | 실패 시 |

**Status mapping**:
- `ToolResult.success=True` → `Status(UNSET)`.
- `ToolResult.success=False` → `Status(ERROR)` + `error.type=error_class` (whitelist 통과값).

**PII rule**: 도구 입력/출력 payload는 **부착하지 않는다**. E5의 whitelist만 통과 허용.

## E5. FilteredAttributes

span 속성 부착 전 통과하는 필터 함수의 입출력.

```python
# src/kosmos/observability/otel_bridge.py
from kosmos.observability.event_logger import _ALLOWED_METADATA_KEYS

def filter_metadata(raw: dict[str, object]) -> dict[str, AttributeValue]:
    """Whitelist 통과 + AttributeValue 호환 타입만 반환."""
```

**Whitelist source**: `_ALLOWED_METADATA_KEYS = {"tool_id", "step", "decision", "error_class", "model"}` (단일 진실 소스, `event_logger.py:45-47`).

**Type coercion rules**:
- `str | int | float | bool | None` → 그대로 통과.
- `list[primitive]` → 그대로 통과.
- 그 외(dict/bytes/객체) → **drop**, 경고 로그 없음(noise 방지).

**Invariant**: 동일 입력에 대해 이 함수와 `ObservabilityEventLogger`의 whitelist 필터 결과 키 집합이 **정확히 같아야** 한다(테스트 `test_otel_bridge_pii.py`로 보장).

## E6. RateLimitRetryCounter

| 항목 | 값 |
|---|---|
| 메트릭 이름 | `kosmos_llm_rate_limit_retries_total` |
| 종류 | Counter (누적) |
| 라벨 | `provider` (str, 예: `friendliai`), `model` (str) |
| 증가 시점 | `LLMClient.generate_stream`에서 FriendliAI가 `429` 반환 → `Retry-After` 헤더 존중 후 재시도 직전에 +1 |
| 리셋 정책 | 프로세스 lifetime 내 누적, 프로세스 종료 시 소멸 |

**기존 시스템과의 관계**: 이 카운터는 `MetricsCollector` 인터페이스의 기존 규약을 따른다(기존 카운터 추가와 동일 방식). OTel Metrics로의 이관은 본 epic 범위 밖(Deferred).

## Relationships

```
TracingSettings ──1─┐
                    ▼
            TracerProvider (OTel SDK)
                    │
                    ├── InvokeAgentSpan (query 1개)
                    │         │
                    │         ├── ChatSpan (n개, 순차)
                    │         │      └── 429 시 RateLimitRetryCounter++
                    │         │
                    │         └── ExecuteToolSpan (m개, 순차 또는 병렬)
                    │
                    └── BatchSpanProcessor → OTLPSpanExporter(http/protobuf) → Langfuse
```

Span 속성 부착은 항상 `FilteredAttributes`를 거친다(`otel_bridge.filter_metadata`).

## Constitution Principle III gate

- 신규 Pydantic v2 모델: `TracingSettings` (frozen, extra=forbid, 필드마다 타입 지정 + description). PASS.
- OTel Span/Tracer는 외부 라이브러리 객체 → Pydantic 경계 바깥. PASS.
- `FilteredAttributes` 반환 타입은 OTel SDK의 `AttributeValue` 유니온(`str|bool|int|float|Sequence[...]`)으로 고정. `Any` 사용 없음. PASS.
