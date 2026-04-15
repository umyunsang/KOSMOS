# Phase 0 Research — Observability (OTel GenAI + Langfuse)

**Feature**: `021-observability-otel-genai`
**Date**: 2026-04-15

본 문서는 plan.md의 Technical Context 결정이 의존하는 외부 레퍼런스를 정리하고, Constitution Principle I("Reference-Driven Development") 게이트 통과를 위해 각 설계 결정을 **docs/vision.md § Reference materials 또는 OTel 공식 semconv** 중 하나에 1:1 매핑한다.

## Deferred Items Validation (Principle VI gate)

spec.md "Scope Boundaries & Deferred Items" 섹션을 스캔한 결과:

| Item | Tracking Issue | Action |
|---|---|---|
| Production OTLP collector 운영 | `NEEDS TRACKING` | `/speckit-taskstoissues`가 플레이스홀더 Issue 생성 |
| OTel Logs 시그널 통합 | `NEEDS TRACKING` | 동일 |
| Span 샘플링/필터링 정책 | `NEEDS TRACKING` | 동일 |
| 자동 평가(eval)와 Langfuse datasets 연동 | `NEEDS TRACKING` | 동일 |

spec 전반 free-text 스캔: "separate epic", "future epic", "Phase 2+", "v2", "deferred to", "later release", "out of scope for v1" 패턴을 검색한 결과, **Deferred Items 표에 등록되지 않은 미등록 deferral 없음**. Principle VI GATE 통과.

## Decision log

### D1. 수동 span authoring (auto-instrumentor 거부)

- **Decision**: OTel GenAI span을 `LLMClient.generate_stream`, `ToolExecutor.dispatch`, `engine/query.query` 안에서 `tracer.start_as_current_span(...)`로 **직접** 생성한다. `opentelemetry-instrumentation-openai-v2`, OpenLLMetry(traceloop-sdk), LangSmith wrapper 등은 사용하지 않는다.
- **Rationale**:
  - KOSMOS의 LLM 호출은 FriendliAI Serverless에 `httpx.AsyncClient`로 직접 요청(OpenAI-compatible endpoint). `openai` Python SDK의 `ChatCompletion` 객체가 존재하지 않기 때문에 auto-instrumentor가 훅 걸 대상이 원천적으로 없다.
  - AGENTS.md § Hard rules: "Never add a dependency outside a spec-driven PR" — 의존성 최소화 원칙.
  - 수동 authoring은 속성 이름·값 통제가 명확해 PII whitelist 재사용이 단순해진다.
- **Alternatives considered**:
  - `opentelemetry-instrumentation-httpx`: span이 "HTTP client" 수준에서만 생기고 GenAI 속성(gen_ai.*)이 자동으로 붙지 않음. 결국 수동 속성 부착이 필요 → 이점 없음.
  - OpenLLMetry(Traceloop): 프로젝트 스타일상 runtime monkey-patch + Decorator. AGENTS.md 최소 의존 원칙 위배.
- **Reference**:
  - OTel Python semconv: `opentelemetry-semantic-conventions` 패키지의 `gen_ai` 모듈 상수(v1.40, Development 안정성).
  - docs/vision.md § Claude Agent SDK — async generator tool loop: 자체 tracing 관례를 파생 frameworks에 위임하지 않는 관례.

### D2. Span 이름과 속성 — OTel GenAI semconv v1.40

- **Decision**: 세 종류 span의 이름·속성 셋은 OTel GenAI semconv v1.40을 따른다.
  - `invoke_agent kosmos-query` — 속성: `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name=kosmos-query`, `gen_ai.conversation.id=<session_id>`
  - `chat` — 속성: `gen_ai.operation.name=chat`, `gen_ai.provider.name=friendliai`, `gen_ai.request.model=<model>`, `gen_ai.response.model=<model>`, `gen_ai.usage.input_tokens=<int>`, `gen_ai.usage.output_tokens=<int>`, `gen_ai.response.finish_reasons=[...]`
  - `execute_tool {tool_id}` — 속성: `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name=<tool_id>`, `gen_ai.tool.type=function`
- **Rationale**: Langfuse는 OTel GenAI semconv 속성을 1급으로 인식해 token 사용량·모델 필터링을 자동 제공. 속성 이름을 임의로 쓰면 Langfuse 대시보드의 gen_ai 전용 뷰가 비활성화된다.
- **Alternatives considered**:
  - `gen_ai.system` (v1.37 이전 이름): v1.37에서 `gen_ai.provider.name`로 rename됨. **금지**(Epic #463 제약 #7).
  - 자체 attribute key(`kosmos.llm.*`): Langfuse 자동 인식 손실. 기각.
- **Reference**: https://opentelemetry.io/docs/specs/semconv/gen-ai/ (v1.40 spans, Development stability).

### D3. OTLP HTTP/protobuf 프로토콜 고정

- **Decision**: `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`를 기본값으로 고정. gRPC 경로는 제공하지 않는다.
- **Rationale**: Langfuse OTel endpoint(`/api/public/otel/v1/traces`)는 HTTP/protobuf만 수신한다. 잘못된 프로토콜로 export 시 연결 에러가 발생해 애플리케이션 로그 소음만 늘어남.
- **Alternatives considered**:
  - gRPC(:4317): Langfuse 미수신. 기각.
  - OTLP/JSON(HTTP): SDK 지원은 있으나 protobuf 대비 페이로드 효율이 낮고 Langfuse 권장 구성이 protobuf. 기각.
- **Reference**: Langfuse 공식 문서 "Self-hosting v3 — OpenTelemetry ingestion" (2026-04-01 최신본).

### D4. `OTEL_SDK_DISABLED=true` no-op 경로

- **Decision**: 환경변수 `OTEL_SDK_DISABLED=true`이면 TracerProvider를 `NoOpTracerProvider`로 세팅하고 BatchSpanProcessor/Exporter를 전혀 초기화하지 않는다. 테스트 스위트의 CI 실행에서 기본값이 된다(CI env에서 주입).
- **Rationale**: CI는 네트워크 제한 환경. OTel SDK는 `OTEL_SDK_DISABLED`를 표준 환경변수로 인식한다(OTel Configuration spec). 모든 OTel API 호출은 no-op이 되어 기존 테스트가 영향 받지 않는다.
- **Alternatives considered**:
  - 자체 feature flag(`KOSMOS_OTEL_ENABLED`): OTel 표준 변수와 이중 경로 발생. 기각.
- **Reference**: https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/ (`OTEL_SDK_DISABLED`).

### D5. Stability opt-in: `gen_ai_latest_experimental`

- **Decision**: `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`를 기본값으로 지정(애플리케이션 부팅 시 미설정이면 주입).
- **Rationale**: v1.40 GenAI 속성은 전부 "Development" 안정성. opt-in 없이는 semconv 라이브러리가 일부 신규 속성을 노출하지 않는다. 환경변수로 명시 → 향후 Stable 승급 시 한 줄로 이전.
- **Alternatives considered**: opt-in 안 함 → 최신 속성 미사용. 기각.
- **Reference**: OTel semconv migration guide, `OTEL_SEMCONV_STABILITY_OPT_IN` 문서.

### D6. 스트리밍 usage 집계(청크별 기록 금지)

- **Decision**: `LLMClient.generate_stream`은 스트리밍 응답을 순차 consume하며 토큰·content를 내부에서 누적, **스트림 종료 시점에만** `chat` span 속성으로 1회 기록한다.
- **Rationale**: OTel GenAI semconv는 span당 하나의 usage 속성 쌍(`input_tokens`, `output_tokens`)만 규정. 청크마다 속성을 갱신하면 Langfuse 파싱 비용 증가 + 속성 덮어쓰기 부작용.
- **Alternatives considered**:
  - 청크마다 event 추가: 가능하나 본 epic 범위 밖(D11 참조).
- **Reference**: OTel GenAI spec — streaming usage aggregation convention. 내부 레퍼런스: `src/kosmos/llm/usage.py`의 기존 누산 패턴.

### D7. 429 retry counter를 별도 metric으로 추가

- **Decision**: FriendliAI가 `429 Too Many Requests`를 반환해 LLM 재시도가 발생할 때마다 `kosmos_llm_rate_limit_retries_total` counter를 1 증가. `Retry-After` 헤더 존중 기존 로직(spec 019)은 변경 없음.
- **Rationale**: 재시도가 span 내 숨어 있으면 운영자가 "오늘 몇 번의 429가 있었나"를 쉽게 못 본다. Counter는 Langfuse의 metric 뷰에서 시계열로 즉시 확인 가능.
- **Alternatives considered**:
  - 재시도마다 별도 span 생성: 노이즈. 기각(spec edge case 참조).
- **Reference**: docs/vision.md § LangGraph `RetryPolicy` + 019 spec의 429 처리.

### D8. PII whitelist 재사용 — 단일 진실 소스 보존

- **Decision**: `src/kosmos/observability/event_logger.py`의 `_ALLOWED_METADATA_KEYS` frozenset(`tool_id`, `step`, `decision`, `error_class`, `model`)을 `otel_bridge.py`에서 import하여 span 속성 prefilter에도 사용한다. 중복 whitelist 정의 금지.
- **Rationale**: 두 곳에 whitelist를 두면 한쪽만 업데이트되는 drift 위험. Constitution II(fail-closed) 유지.
- **Reference**: 기존 `src/kosmos/observability/event_logger.py:45-47` 주석 "(AC-A10)".

### D9. Docker Compose — Langfuse v3 자체 호스팅

- **Decision**: Langfuse v3 공식 `docker-compose` 참조(langfuse-k8s 및 self-hosting docs)를 기반으로 `docker-compose.dev.yml` 작성. 구성: `langfuse-web`(UI/API), `langfuse-worker`, `postgres`, `redis`, `clickhouse`, `minio`(S3 호환). 포트: Web 3000, OTLP ingest 3000/api/public/otel.
- **Rationale**: Langfuse v3는 ClickHouse(trace/observation 저장)·MinIO(event blob)·Redis(queue)를 필수로 한다. v2 이미지는 공식 deprecated.
- **Alternatives considered**:
  - Langfuse Cloud: spec OoS(자체 호스팅 전제).
  - v2 + Postgres only: 더 간단하나 공식 deprecated. 기각.
- **Reference**: https://langfuse.com/self-hosting/docker-compose (2026-04-01 버전 체크).

### D10. `.env.example` 엔트리 블록 & base64 auth 헤더

- **Decision**: `.env.example`에 다음 블록 추가:
  ```
  # Observability (OTel + Langfuse)
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:3000/api/public/otel
  OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
  OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20<base64(public_key:secret_key)>
  OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
  # OTEL_SDK_DISABLED=true   # uncomment to disable in CI/offline
  ```
- **Rationale**: Langfuse의 OTLP endpoint는 HTTP Basic auth(public_key:secret_key, base64)를 요구. 주석으로 CI 비활성화 팁 제공.
- **Reference**: Langfuse OTel ingestion guide + OTel `OTEL_EXPORTER_OTLP_HEADERS` spec.

### D11. Out of scope (재확인)

- 프로덕션 collector, OTel Logs, sampling 정책, eval/datasets 연동은 spec에 이미 Deferred로 등록됨(본 Research에서 추가 action 없음).

## Integration patterns

### IP1. Tracer 주입 방식

- `TracerProvider`를 애플리케이션 부팅 시 1회 초기화(`tracing.setup_tracing()` 팩토리). `LLMClient`, `ToolExecutor`, `query()`에는 **모듈 레벨 `trace.get_tracer(__name__)`** 호출로 tracer를 얻음(OTel 표준 패턴).
- 장점: 별도 constructor DI 없이도 동일 프로세스의 TracerProvider에 연결된다. `setup_tracing()`을 호출하지 않으면 `NoOpTracer`가 자동 반환 → 기존 동작 100% 보존.

### IP2. BatchSpanProcessor 구성

- `BatchSpanProcessor(OTLPSpanExporter(endpoint=..., protocol="http/protobuf"))`.
- Default queue size(2048), default export timeout(30s), default scheduled delay(5s)를 그대로 사용. `OTEL_BSP_*` 환경변수로 override 가능(OTel spec).

### IP3. Span 속성 whitelist prefilter

- `otel_bridge.filter_metadata(d: dict) -> dict` — `_ALLOWED_METADATA_KEYS`를 import하여 사용. span 생성 시 `span.set_attributes(filter_metadata(raw))`.

### IP4. 에러 → span 상태 매핑

- OTel `Status(StatusCode.ERROR)` + `span.record_exception(exc)`. `span.set_attribute("error.type", exc.__class__.__name__)`.
- 기존 `ObservabilityEvent.success=False` 이벤트는 그대로 별도 채널로 emit — 변경 없음.

## Reference → Design mapping (Constitution Principle I gate)

| Design decision | Reference source | Layer |
|---|---|---|
| 수동 span authoring | OTel semconv v1.40 (Python), AGENTS.md 최소 의존 원칙 | Observability (cross-cutting) |
| `gen_ai.provider.name` 사용 | OTel semconv v1.37 rename note | Observability |
| OTLP HTTP/protobuf | Langfuse self-hosting 공식 docs | Export |
| `OTEL_SDK_DISABLED` no-op | OTel Configuration spec (env vars) | Bootstrap |
| PII whitelist 재사용 | 기존 `event_logger.py:_ALLOWED_METADATA_KEYS` + Constitution II | Observability |
| Streaming usage aggregation | OTel GenAI spec + `src/kosmos/llm/usage.py` 누산 | LLM Client |
| 429 retry counter | docs/vision.md § LangGraph RetryPolicy + 019 spec | LLM Client |
| BatchSpanProcessor | OTel Python SDK default patterns | Export |
| Langfuse v3 자체 호스팅 | Langfuse self-hosting docker-compose 공식 | Dev stack |
| Parent span = session | docs/vision.md § Query Engine (async generator loop) | Query Engine |

Gate: **all design decisions mapped to a concrete reference**. Constitution Principle I PASS.
