# Feature Specification: Observability — OpenTelemetry GenAI + Langfuse

**Feature Branch**: `021-observability-otel-genai`
**Created**: 2026-04-15
**Status**: Draft
**Input**: Epic #463 — Phase 2 요구조건 (OTel GenAI semconv v1.40 수동 span, Langfuse v3 자체 호스팅, MetricsCollector/ObservabilityEventLogger 브리지, OTLP http/protobuf, `OTEL_SDK_DISABLED` no-op 경로, `gen_ai.provider.name` 명칭, `gen_ai_latest_experimental` opt-in).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Developer traces a production agent failure end-to-end (Priority: P1)

한 운영자가 Phase 2 시나리오 실행 중 "경로 안전" 질의가 실패했다고 보고한다. 개발자는 Langfuse UI를 열어 해당 세션 ID로 trace 하나를 조회한다. 사용자 질의 → LLM 호출(스트리밍) → 도구 실행(KOROAD 어댑터) → LLM 재호출 → 최종 응답까지 **하나의 부모-자식 span 트리**로 연결되어, 어느 단계에서 실패가 발생했는지, 각 단계가 몇 ms 걸렸는지, LLM이 몇 토큰을 사용했는지, 도구가 어떤 오류 클래스를 반환했는지 한 화면에서 파악할 수 있다.

**Why this priority**: KOSMOS는 멀티턴·멀티도구 루프라 blackbox 로그만으로는 장애 원인을 찾을 수 없다. Phase 2 시나리오가 본격화되기 전 "최소 1개 trace로 전체 흐름을 볼 수 있는" 관측성이 선행 조건이다 (Infrastructure Initiative SC-7).

**Independent Test**: 테스트용 에이전트 세션을 로컬에서 1회 실행하고, 구동된 Langfuse 인스턴스의 trace 탐색 화면에서 해당 `session_id` 가 달린 trace를 열어 (a) 부모 `invoke_agent` span (b) 자식 `chat` span (c) 자식 `execute_tool` span 세 종류가 모두 계층 구조로 나타나는지 확인.

**Acceptance Scenarios**:

1. **Given** 한 사용자 세션이 LLM 호출 1회와 도구 호출 1회를 포함한다, **When** 세션이 정상 완료되면, **Then** Langfuse는 1개의 parent span(`invoke_agent`)과 그 아래 2개의 자식 span(`chat`, `execute_tool <tool_id>`)을 동일한 trace ID로 수신한다.
2. **Given** LLM 스트리밍 호출 중 FriendliAI가 `429` 응답을 반환해 재시도가 발생한다, **When** 재시도가 성공한다, **Then** 해당 `chat` span은 하나로 유지되고 재시도는 `kosmos_llm_rate_limit_retries_total` counter에 1회 증가되며 span 상태는 `UNSET`으로 마감된다.
3. **Given** 도구 실행이 Pydantic 검증 실패로 에러를 던진다, **When** 에이전트 루프가 이를 캐치한다, **Then** `execute_tool` span의 상태는 `ERROR`로 기록되고, `error.type` 속성에 에러 클래스가 달린다.

---

### User Story 2 — SRE monitors token spend and streaming throughput (Priority: P2)

운영 책임자가 "지난 24시간 동안 어느 도구가 가장 많은 LLM 입력 토큰을 유발했는지"를 주간 리뷰에서 확인해야 한다. Langfuse 대시보드에서 모델별·도구별 토큰 합계와 호출 횟수를 곧바로 필터링할 수 있고, 각 `chat` span의 시작~종료 duration으로 총 응답 시간을 확인할 수 있다.

**Why this priority**: K-EXAONE 서버리스는 토큰당 과금 모델이며, 도구 호출 루프가 비정상적으로 길어지면 비용이 수 배 증가한다. 장애가 없어도 관측이 되지 않으면 비용 통제 자체가 불가능하다.

**Independent Test**: 임의의 프롬프트로 스트리밍 chat 호출 1회를 수행한 뒤 Langfuse의 usage 리포트에서 입력/출력 토큰과 총 소요시간이 각각 별개 값으로 기록되었는지 확인.

**Acceptance Scenarios**:

1. **Given** 스트리밍 chat 호출이 완료되었다, **When** Langfuse가 span을 수신한다, **Then** 해당 span에는 입력 토큰, 출력 토큰, 모델명, provider 이름이 모두 기록되어 있다.
2. **Given** 동일한 프롬프트로 5회 반복 호출한다, **When** Langfuse 대시보드에서 시간 범위를 주간으로 필터링한다, **Then** 모델별 총 토큰 합계가 5회분의 합과 일치한다(±0).

---

### User Story 3 — CI runs without an OTLP collector (Priority: P1)

개발자가 CI에서 유닛 테스트를 돌린다. CI 컨테이너에는 Langfuse나 OTLP collector가 실행되어 있지 않고, 인터넷 접근도 제한되어 있다. 환경변수로 텔레메트리를 끄면, 어떤 span export 시도도 일어나지 않고 테스트는 정상 통과한다. 텔레메트리가 꺼져 있는 상태에서도 기존 `ObservabilityEventLogger`와 `MetricsCollector` 로직은 동일하게 동작한다.

**Why this priority**: 텔레메트리 장애가 CI/배포 파이프라인을 중단시키면 안 된다. OTel 레이어는 **항상 옵셔널**이어야 한다 (AGENTS.md § Hard rules — 외부 의존성 추가 시 spec-driven PR).

**Independent Test**: `OTEL_SDK_DISABLED=true` 환경에서 전체 pytest 스위트를 실행한 뒤, (a) 모든 기존 테스트가 통과하는지, (b) OTLP 엔드포인트로의 네트워크 시도가 0회였는지(캡처 기반) 확인.

**Acceptance Scenarios**:

1. **Given** `OTEL_SDK_DISABLED=true`가 설정되어 있다, **When** `pytest` 전체 스위트를 실행한다, **Then** 모든 테스트가 통과하고 외부 네트워크 호출은 발생하지 않는다.
2. **Given** `OTEL_EXPORTER_OTLP_ENDPOINT`가 지정되지 않았다, **When** 에이전트 세션이 실행된다, **Then** 애플리케이션은 경고만 남기고 정상 실행을 계속한다(예외를 던지지 않는다).
3. **Given** OTLP 엔드포인트가 설정되어 있지만 collector가 다운되어 있다, **When** 에이전트 루프가 span을 export 시도한다, **Then** export 실패는 내부적으로 로깅되고 사용자 요청은 정상 응답된다.

---

### User Story 4 — Operator brings up the local Langfuse stack with one command (Priority: P2)

새로 합류한 개발자가 README의 "Observability 로컬 구동" 절을 읽고 `docker compose -f docker-compose.dev.yml up` 한 줄로 Langfuse UI·API 서버·필수 백엔드(Postgres, Redis, ClickHouse, MinIO 호환 오브젝트 스토리지)를 모두 띄운다. `.env.example`를 `.env`로 복사한 뒤 환경변수 몇 개(엔드포인트, public/secret key base64)만 채우면 로컬 에이전트 세션 trace가 바로 Langfuse UI에 나타난다.

**Why this priority**: 자체 호스팅 Langfuse v3는 4개의 백엔드 서비스가 필요하며, 수동 설치는 시연·온보딩 장벽이 크다. 1-커맨드 부트스트랩이 없으면 "관측성 사용법" 자체가 채택되지 않는다.

**Independent Test**: 깨끗한 개발 머신에서 README 지침대로 3개 명령어(`cp .env.example .env`, 값 채움, `docker compose up`)만으로 Langfuse UI가 뜨고, 샘플 에이전트 호출이 trace로 수신되는지 확인.

**Acceptance Scenarios**:

1. **Given** 개발자가 리포지토리를 방금 클론했다, **When** `docker compose -f docker-compose.dev.yml up -d`를 실행한다, **Then** Langfuse UI(:3000)가 healthy 상태로 뜨고, 종속된 모든 백엔드 컨테이너가 정상 기동한다.
2. **Given** Langfuse가 로컬에서 실행 중이다, **When** 개발자가 한 번 에이전트 호출을 수행한다, **Then** 10초 이내에 Langfuse UI의 "Traces" 탭에 그 호출이 나타난다.

---

### Edge Cases

- Langfuse 엔드포인트가 **HTTP/protobuf만** 수신하고 gRPC는 받지 않을 때: export가 gRPC로 시도되면 연결 실패하되, 애플리케이션 흐름은 중단되지 않아야 한다. 기본 설정은 반드시 HTTP/protobuf.
- OTel semantic conventions가 "Development" 안정성이라 향후 breaking rename 가능: 발생 시 KOSMOS는 최신 rename을 반영하되, 이전 속성명은 유지하지 않는다(수동 span이라 매핑이 명확하므로).
- `event.metadata`에 실수로 PII 키(예: `user_email`)가 포함된 경우: 기존 `ObservabilityEventLogger`의 whitelist가 키를 제거하는 기존 동작을 유지하면서, OTel span 속성으로도 **동일 whitelist 이후의 값만** 전파.
- FriendliAI `429` + `Retry-After` 헤더가 온 경우: 재시도 카운터 metric은 증가하되, LLM chat span 하나 안에서 재시도가 일어난 것으로 기록(재시도마다 별개 span을 만들지 않는다).
- 스트리밍 응답 중간에 연결이 끊긴 경우: 그때까지 누적된 사용량(usage)만 span에 기록하고, span 상태는 `ERROR`로 마감.
- Langfuse 서버가 다운되어 export backlog가 메모리에 쌓이는 경우: BatchSpanProcessor의 큐가 가득 차면 신규 span이 폐기(drop)되고 애플리케이션은 영향받지 않는다.

## Requirements *(mandatory)*

### Functional Requirements

#### Spans (what operations are traced)

- **FR-001**: 사용자의 한 질의가 에이전트 루프에 진입하면 시스템은 `invoke_agent kosmos-query` 이름의 부모 span을 생성한다. 이 span은 `gen_ai.conversation.id` 속성으로 세션 식별자를 달고, 자식 span들이 모두 이 부모 아래에 묶인다.
- **FR-002**: LLM 스트리밍 호출이 발생하면 시스템은 `chat` 이름의 자식 span을 생성하고, 호출이 끝나면(또는 에러로 마감되면) 입력/출력 토큰 수, 모델명, provider 이름, 마감 사유(finish reason)를 span 속성으로 남긴다.
- **FR-003**: 도구 실행이 발생하면 시스템은 `execute_tool <tool_id>` 이름의 자식 span을 생성하고, 도구 ID와 실행 성공 여부를 span 속성으로 남긴다. 도구가 예외를 던지면 span 상태는 `ERROR`로 마감되고 에러 클래스가 속성에 기록된다.
- **FR-004**: 세 종류의 span(`invoke_agent`, `chat`, `execute_tool`)은 OpenTelemetry GenAI Semantic Conventions v1.40을 따르며, GenAI 관련 속성은 `gen_ai.*` 네임스페이스를 사용한다. 구체적으로 provider 식별은 `gen_ai.provider.name`을 사용한다(과거 `gen_ai.system`은 사용하지 않는다).

#### Streaming & retries

- **FR-005**: 스트리밍 chat 호출에서 토큰 사용량은 스트림이 완료된 시점에 **집계된 값 하나**로 span에 기록한다(청크당 기록하지 않는다).
- **FR-006**: LLM 호출이 HTTP 429를 받아 재시도를 수행할 때마다 시스템은 별도의 counter metric을 1 증가시킨다. 이 counter에는 provider 이름과 모델명이 label로 붙는다. 재시도가 일어나도 `chat` span은 하나로 유지된다.

#### Export & configuration

- **FR-007**: 완성된 span들은 OTLP **HTTP/protobuf** 프로토콜로 export한다. gRPC는 사용하지 않는다.
- **FR-008**: 시스템은 다음 환경변수를 인식한다: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SDK_DISABLED`, `OTEL_SEMCONV_STABILITY_OPT_IN`. 기본값은 `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` 및 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`.
- **FR-009**: `OTEL_SDK_DISABLED=true`가 설정되면 OTel SDK는 초기화되지 않고 어떠한 export 시도도 하지 않는다. 이 경로에서 기존 기능의 모든 자동화 테스트가 통과한다.
- **FR-010**: OTLP 엔드포인트가 설정되지 않았거나 collector가 도달 불가능한 경우, 시스템은 경고 로그 1회를 남기고 애플리케이션 흐름을 중단하지 않는다. export 실패는 사용자 요청의 응답 성공/실패에 영향을 주지 않는다.

#### Bridge with existing observability

- **FR-011**: 기존 `ObservabilityEventLogger`의 PII 키 whitelist(`tool_id`, `step`, `decision`, `error_class`, `model`)는 변경 없이 유지된다. whitelist를 통과한 값만 OTel span 속성으로 전파될 수 있다.
- **FR-012**: 기존 `MetricsCollector`가 기록하는 카운터·히스토그램·게이지는 동작이 변하지 않는다. OTel metric은 **추가 레이어**로서 존재하며, 기존 수집값을 중복 기록하거나 대체하지 않는다.
- **FR-013**: 기존 `ObservabilityEvent` 이벤트 타입들(`llm_call`, `permission_decision`, `tool_call` 등)은 그대로 유지되며, OTel span과 병렬로 발생한다.

#### Local development stack

- **FR-014**: 리포지토리에는 `docker-compose.dev.yml` 파일이 있어, 한 줄 명령으로 Langfuse UI와 그 의존 백엔드(Postgres, Redis, ClickHouse, S3 호환 오브젝트 스토리지)를 로컬에 구동할 수 있다.
- **FR-015**: `.env.example` 파일은 텔레메트리에 필요한 모든 환경변수의 예시와 설명을 포함한다. 실 키는 커밋되지 않는다.

#### Dependencies constraint

- **FR-016**: 외부 런타임 의존성은 `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-semantic-conventions` **정확히 3개만** 추가한다. auto-instrumentor 계열(`opentelemetry-instrumentation-*`, `openllmetry`, `traceloop` 등)은 추가하지 않는다.

### Key Entities

- **Trace**: 한 사용자 질의 → 최종 응답 사이의 모든 span 집합. `session_id`로 묶인다.
- **Span**: 에이전트 루프 내 한 구간(에이전트 전체 호출 / 1회 LLM chat / 1회 도구 실행)을 나타내는 기록. 이름·속성·시작·종료 타임스탬프·상태를 가진다.
- **Usage**: LLM 호출 시 입력 토큰·출력 토큰·모델·provider 집계. `chat` span의 속성으로 기록된다.
- **Retry counter**: `429` 재시도 횟수를 provider/모델별로 집계하는 metric.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (단일 trace 가시성): 로컬 Langfuse 인스턴스에서 한 세션의 전체 호출(사용자 질의 → LLM → 도구 → LLM → 응답)을 **1개의 trace**로 열람할 수 있다. 그 trace 내에서 부모-자식 계층이 최소 3단계 이상(에이전트 → chat → tool) 표현된다.
- **SC-002** (사용량 기록 완전성): 스트리밍 chat 호출 100회 연속 테스트에서 **100/100 회** 모두 입력 토큰, 출력 토큰, 모델명, provider 이름이 span 속성에 기록된다.
- **SC-003** (CI 친화성): `OTEL_SDK_DISABLED=true` 환경에서 전체 자동화 테스트 스위트가 100% 통과하며, 테스트 실행 중 외부 네트워크 요청은 0회 발생한다.
- **SC-004** (장애 내성): Langfuse collector가 다운된 상태에서 에이전트 세션을 10회 수행해도 **사용자 응답 실패율 0%**를 유지한다.
- **SC-005** (로컬 부트스트랩 시간): 깨끗한 개발 머신에서 리포지토리 클론 완료 후 Langfuse UI에서 첫 trace를 확인하기까지 걸리는 시간이 **10분 이내**다(Docker 이미지 pull 시간 포함).
- **SC-006** (의존성 예산): `pyproject.toml`에 신규 추가되는 외부 런타임 패키지는 정확히 3개(`opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-semantic-conventions`)다. auto-instrumentor 계열 패키지는 0개다.

## Assumptions

- KSC 심사자 및 운영자는 Docker Desktop 또는 Docker Engine을 로컬에서 실행할 수 있다. Docker가 없는 환경을 위한 대체 부트스트랩은 제공하지 않는다.
- Langfuse v3.x 계열의 자체 호스팅 공식 `docker-compose` 참조 구성을 기반으로 프로젝트 로컬용을 파생한다. Langfuse Cloud는 선택지가 아니다.
- K-EXAONE 호출은 FriendliAI Serverless(OpenAI-compatible)을 통해 순수 `httpx`로 수행되고 있다. `openai` SDK 객체는 존재하지 않기 때문에 auto-instrumentor는 원천적으로 불가능하다. 수동 span authoring만 가능하다.
- 프로덕션 환경(배포용)의 OTLP collector 운영 방식은 이 epic의 범위가 아니다. 로컬 self-hosted 구동만 대상.
- OTel GenAI semconv v1.40은 전 속성이 "Development" 안정성이며, 향후 rename이 있을 수 있다. 그 경우 새 속성명으로 **대체**하며 legacy alias는 유지하지 않는다.
- PII 정책은 기존 `ObservabilityEventLogger`의 whitelist 정책을 단일 진실 소스로 본다. 속성 이름 정책은 OTel semconv를 따르되, **값은** whitelist를 통과한 것만 전파한다.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Auto-instrumentors (`opentelemetry-instrumentation-*`, OpenLLMetry/Traceloop 등)**: KOSMOS의 LLM 호출은 `httpx` 기반 수동 프로토콜이며 auto-instrumentor가 훅 걸 대상이 없다. AGENTS.md 외부 의존성 최소 원칙과도 상충.
- **gRPC OTLP export**: Langfuse는 gRPC를 수신하지 않는다. 프로토콜은 HTTP/protobuf만 지원한다.
- **Log signal(OTel Logs)**: 기존 `logging` + `ObservabilityEventLogger`가 로그 영역을 담당한다. OTel Logs 연계는 이 epic에 포함하지 않는다(trace와 metric만 취급).
- **Langfuse Cloud 계약**: 자체 호스팅 전제. Cloud 계정 연동은 범위 밖.
- **Legacy `gen_ai.system` 속성**: v1.37에서 `gen_ai.provider.name`으로 대체되었으므로 legacy 이름은 **사용하지 않는다**.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Production OTLP collector 운영 (중앙 Langfuse 클러스터, 보존 정책, 대시보드 표준화) | Phase 2 시나리오가 먼저 안정화된 뒤 운영 배포 epic에서 다룸 | Phase 3 Ops | #501 |
| OTel Logs 시그널 통합 (기존 `logging`을 OTel Logs로도 전송) | 이 epic은 trace·metric로 범위를 좁힘. 로그 통합은 별개 설계 결정을 필요로 함 | 이후 관측성 확장 Epic | #502 |
| Span 샘플링/필터링 정책(대용량 트래픽 대비) | 현재 규모에서 불필요, 1:1 샘플링으로 충분 | Phase 3 Ops | #503 |
| 자동 평가(eval)와 Langfuse datasets 연동 | 평가 파이프라인은 별도 epic에서 설계 | Evaluation Epic | #504 |
