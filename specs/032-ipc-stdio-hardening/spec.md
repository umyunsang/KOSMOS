# Feature Specification: IPC stdio hardening (frame envelope · backpressure · reconnect · at-least-once replay)

**Feature Branch**: `032-ipc-stdio-hardening`
**Created**: 2026-04-19
**Status**: Draft
**Parent Epic**: #1298 (Initiative #2 — Multi-Agent Swarm · ADR-006 Part D-2 Epic A)
**Input**: Epic A #1298 — IPC stdio hardening. Scope: structured frame envelope (version, correlation_id, role, payload, trailer) · backpressure signaling · reconnect handshake · at-least-once replay with transaction_id de-dup. References: CC sourcemap src/services/api/ + src/session/, MCP transports spec (Last-Event-ID semantic), LSP 3.17 JSON-RPC id correlation, Claude Agent SDK stdio strictness, nodejs backpressure + highWaterMark, NDJSON format, idempotency 3-step approach. Hard rule: no new runtime deps. DX→AX framing: 세션 드롭 복구 + 부처 429 가시화 + 민원 중복 제출 차단 + end-to-end correlation_id trace.

## DX → AX migration framing *(mission context)*

KOSMOS의 stdio IPC는 단순 개발자 편의 채널이 아니라 시민 세션이 끊기지 않는 **행정 상담 회선**이다. 전화 민원실은 "다시 거세요"가 허용되지만 세션 하네스는 부처 호출이 이미 발사된 상태에서 재접속 시 결과를 돌려받아야 한다.

| 축 | 기존 DX baseline (오늘의 시민·공무원 워크플로) | AX target (KOSMOS 하네스) |
|---|---|---|
| 세션 드롭 복구 | 정부24·HIRA·KOROAD 세션 만료 시 재로그인 + 처음부터 재조회 (시민이 이미 낸 질의 기억 불가) | TUI가 `last_seen_correlation_id` 전달 + 백엔드가 미확인 프레임을 순서대로 재전송 |
| 부처 429 가시화 | 부처 API 한도 소진 시 HTTP 503/429만 노출, 시민은 쿼터 상태 불가시 | 백엔드 `BackpressureSignal` 프레임이 TUI HUD에 "FriendliAI 속도 조절 중 · KMA 일일 쿼터 70%" 식 가시화 |
| 민원 중복 제출 | 시민이 "전송" 버튼을 두 번 눌러 중복 접수되는 사고 빈번 (공공기관 CS 최다 유형 중 하나) | `transaction_id` 기반 idempotency — 동일 tx는 서버에서 deduplicate, 영수증 1장만 발급 |
| 감사 추적 | 부처별 감사 로그 분산, 세션 경계 넘는 인과관계 소실 | 세션 전체에서 `correlation_id` 단일 값으로 OTEL span + `ToolCallAuditRecord`(Spec 024) 연결 |
| 기록 포맷 | 텍스트 로그 ad-hoc | NDJSON (newline-delimited JSON) 프레임 — `jq` 등 표준 도구로 사후 분석 가능 |

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 세션 드롭 복구 (Priority: P1)

시민이 HIRA에 "서울 강남구 응급실 실시간 가용 병상" 질의를 LLM에 전달한 직후 TUI가 crash하거나 백엔드가 재시작된다. 시민은 터미널을 다시 열고 기존 세션에 재접속한다. KOSMOS는 시민이 놓친 모든 중간 응답(LLM 스트리밍 토큰 + tool-call trailer + 최종 답변)을 순서 유지한 채 재전송하고, 이미 확인한 프레임은 중복 전달하지 않는다.

**Why this priority**: P1. 공공 민원 상담 품질의 가장 큰 체감 지표는 "내가 한 말을 기억하는가". 드롭 복구가 되지 않으면 시민은 KOSMOS 하네스를 "다시 거세요"라는 구닥다리 민원실로 인식하며, 부처 API 호출이 진행 중일 때 세션이 끊기면 호출 결과가 영구 소실되어 사고로 이어진다(예: KOROAD 사고기록 조회 재발주 → data.go.kr 쿼터 중복 소모).

**Independent Test**: `kill -9 <backend-pid>` 중간 주입 시나리오로 검증 가능. TUI가 재접속 핸드셰이크로 `last_seen_correlation_id`를 보내면 백엔드가 그 이후의 모든 버퍼된 프레임을 순서대로 재전송하고 세션이 재개된 후 시민이 정상적으로 후속 질의를 이어갈 수 있어야 한다.

**Acceptance Scenarios**:

1. **Given** 시민이 `correlation_id=C-42`로 시작된 HIRA 조회를 진행 중이고 백엔드가 3개 프레임(`payload_start` / `tool_result` / `payload_delta`)을 보냈으나 TUI가 2개만 수신한 상태, **When** TUI가 crash 후 재시작하여 `resume(session_id=S, last_seen_correlation_id=C-42, last_seen_frame_seq=2)`를 전송, **Then** 백엔드는 3번째 프레임부터 정확히 순서 유지한 채 재전송하고, 시민 화면에 중복·누락·순서바뀜 없이 스트림이 이어진다.
2. **Given** 백엔드가 5개 프레임을 ack 없이 보낸 후 백엔드 프로세스가 crash, **When** 백엔드가 재시작되고 TUI가 resume 요청, **Then** 백엔드는 5개 프레임을 모두 재전송하고 tx idempotency로 KOROAD 실제 호출은 1회만 발생한다(쿼터 낭비 없음).
3. **Given** 유효하지 않은 `last_seen_correlation_id`가 resume에 포함, **When** 핸드셰이크 처리, **Then** 백엔드는 명시적 `resume_rejected` 프레임으로 거절 사유(예: `session_expired`, `correlation_unknown`)를 돌려주고 세션을 새로 시작하도록 유도한다.

---

### User Story 2 — 부처 429 / FriendliAI 쿼터 가시화 (Priority: P1)

시민이 연속 질의를 발사하고 있는데 FriendliAI LLM 스트리밍이 429 상태에 진입하거나 KMA 기상특보 호출이 일일 쿼터에 근접한다. 시민은 "왜 느려졌는지"를 터미널 로그를 뒤지지 않고도 TUI 상단 상태바에서 즉시 알 수 있어야 한다.

**Why this priority**: P1. Spec 019 (LLM 429 retry) · Spec 023 (NMC freshness) · 향후 Spec 031 CBS 구독 모두 out-of-band signal이 "언제 속도가 느려지는지"를 시민에게 알려야 한다. 가시화가 없으면 시민은 KOSMOS를 버그로 인식하고 이탈한다. 이는 PIPA §35 열람권 해석의 간접적 파생(시민이 자기 요청의 처리 상태를 열람할 권리)이며, 행정 AX 전환의 최소 요건이다.

**Independent Test**: 백엔드가 인위적으로 `BackpressureSignal(kind=llm_rate_limit, severity=warn, retry_after_ms=2000)` 프레임을 발사했을 때 TUI HUD가 1 animation frame 이내에 "LLM 속도 조절 중 · 2 s 후 재개"를 표시하고, 시민이 신규 입력을 시도하면 TUI가 backpressure 상태를 존중해 입력을 큐잉하거나 부드럽게 거절한다.

**Acceptance Scenarios**:

1. **Given** 백엔드가 FriendliAI 429를 감지하여 `BackpressureSignal(kind=llm_rate_limit, retry_after_ms=2000)` 프레임 발사, **When** TUI가 수신, **Then** 상단 상태바에 Korean + English 텍스트 "LLM 속도 조절 · ~2s" 표시하며 이 텍스트는 `source_agency=friendli` 속성을 포함한 OTEL span에 기록된다.
2. **Given** TUI 입력 버퍼가 high-water-mark(예: 64개 프레임)에 도달, **When** 백엔드가 `BackpressureSignal(kind=tui_ingest_saturated)` 프레임 발사, **Then** 백엔드는 새 outbound 프레임을 일시 중단하고 TUI drain 후 `resume_emit` 프레임으로 재개한다.
3. **Given** 시민이 backpressure 상태에서 신규 입력 전송, **When** TUI가 처리, **Then** 시민 입력은 로컬 큐에 유지되며 drain 완료 후 순서대로 전송; 명시적 에러 없이 처리.

---

### User Story 3 — 민원 중복 제출 차단 (Priority: P1)

시민이 `lookup(mode=fetch, tool_id=gov24.apply_submit, params=...)` 호출을 발사한 직후 네트워크 flap으로 응답이 늦어지자 같은 명령을 다시 누른다. KOSMOS는 두 번째 요청을 transaction_id 기반으로 감지하고 첫 번째 호출의 결과를 그대로 반환한다. 민원은 한 번만 접수된다.

**Why this priority**: P1. 정부24 민원 제출, HIRA 진료기록 열람 신청, MOHW 출산지원금 재신청 등 "한 번만" 실행되어야 하는 irreversible-write 도구(Spec 024 `is_irreversible=true`)에서 중복 실행은 시민 금전·서류 피해를 유발한다. PIPA §26 수탁자 책임 + Spec 025 V6 AAL 매트릭스 하에서 중복 차단은 법정 안전장치다.

**Independent Test**: 같은 `transaction_id`를 가진 `payload_start` 프레임을 500 ms 간격으로 2회 보내고, 백엔드가 첫 번째는 실제 adapter 호출 + audit log 기록, 두 번째는 "이미 처리됨" 결과를 반환하며 추가 호출 없음을 `ToolCallAuditRecord` 개수(정확히 1)로 검증.

**Acceptance Scenarios**:

1. **Given** TUI가 `correlation_id=C-100, transaction_id=T-abc`로 `gov24.apply_submit` 호출, **When** 응답 지연되어 TUI가 동일 tx로 재시도, **Then** 백엔드는 캐시된 결과를 반환하고 `ToolCallAuditRecord` 1개만 영속화.
2. **Given** 동일 `transaction_id`, 다른 `correlation_id`로 재전송, **When** 백엔드 dedup 로직 진입, **Then** tx 기준으로 dedup (correlation_id 불일치는 경고 로그만 남김).
3. **Given** tx LRU 용량(세션당 512) 초과 후 오래된 tx로 재시도, **When** 백엔드 처리, **Then** cache miss로 판정하여 신규 호출 발사; 단, `is_irreversible=true` 도구는 세션 종료까지 영속 저장(용량 제한 예외).

---

### User Story 4 — end-to-end correlation_id trace (Priority: P2)

개발자/공무원이 시민 민원 조사를 위해 특정 세션의 `correlation_id`로 OTEL Collector·Langfuse·ToolCallAuditRecord 세 축을 조인해 부처 호출 타임라인을 재구성한다.

**Why this priority**: P2. 감사 경계 요구에서 중요하나 시민이 직접 소비하는 기능이 아니다. 기존 Spec 021 OTEL 인프라가 있으므로 본 스펙은 frame envelope에 `correlation_id`/`transaction_id`를 일관 기록하기만 하면 된다.

**Independent Test**: 단일 세션에서 3개 tool을 순차 호출하고 OTEL Collector에 도착한 span·Langfuse trace·`ToolCallAuditRecord` 세 축의 correlation_id가 전부 동일한 값을 포함하는지 검증.

**Acceptance Scenarios**:

1. **Given** 한 세션의 tool 체인, **When** OTEL Collector에서 span 수집, **Then** 모든 span에 `kosmos.ipc.correlation_id`·`kosmos.ipc.transaction_id` 속성 존재.
2. **Given** `correlation_id=C-42`의 세션, **When** `ToolCallAuditRecord` 조회, **Then** 해당 id를 포함한 레코드 집합이 OTEL trace_id 집합과 일관 매핑.

---

### Edge Cases

- **프레임 수신 중 process kill**: `.consumed` 마커가 기록되지 않은 프레임은 재전송 대상; 마커가 있으면 skip.
- **frame envelope schema version mismatch**: 시스템은 `version` 필드 불일치 시 hard-fail (MCP Draft 2024-11-05 전례) — 신·구 버전 교차 실행 방지.
- **TUI가 backpressure 상태에서 강제 종료**: high-water-mark 초과 상태의 버퍼는 flush하지 않고 버림; 재접속 시 resume 경로로만 복구.
- **매우 큰 payload (e.g., 대용량 tool result)**: 단일 프레임 > 1 MiB는 chunked frame으로 분할, trailer의 `final=true` 플래그로 종료 표기.
- **잘못된 JSON newline 포함 payload**: 백엔드는 payload 내부 `\n` 을 이스케이프해 NDJSON line integrity 유지.
- **세션 간 tx 충돌**: `transaction_id`는 세션 스코프 — 다른 세션이 같은 값을 써도 충돌 아님 (dedup LRU 키는 `(session_id, transaction_id)`).
- **Irreversible 도구 tx 영속화**: `is_irreversible=true` 도구의 tx 레코드는 LRU eviction 대상에서 제외; 세션 종료까지 유지.
- **Resume 이전에 tx가 이미 완료**: resume 시 백엔드는 완료된 tx의 최종 결과 프레임을 재전송 (시민은 처음부터 결과를 봤다고 생각하도록).

## Requirements *(mandatory)*

### Functional Requirements

**Frame envelope (FR-001..FR-010)**

- **FR-001**: IPC 프레임은 structured envelope `{version, correlation_id, role, payload, trailer}` 를 갖는다. 모든 프레임은 JSON 객체 단일 라인(NDJSON)으로 직렬화된다.
- **FR-002**: `version` 필드는 envelope 포맷 버전("1.0")과 frame kind discriminator를 함께 담아, 향후 envelope 변경이 frame kind 추가와 독립적으로 이루어지도록 한다.
- **FR-003**: `correlation_id`는 단일 요청-응답 체인을 종적으로 식별하는 UUIDv7 (밀리초 정렬 가능). 최초 발급은 TUI가 사용자 입력 시 수행, 백엔드가 이를 OTEL trace 속성으로 승격한다.
- **FR-004**: `role` 필드는 고정 enum `{tui, backend, tool, llm, notification}` 으로 발신 주체 역할을 명시한다.
- **FR-005**: `payload`는 frame kind 별 discriminated union이며 모든 frame kind는 Pydantic v2 `BaseModel` + `Field(discriminator="kind")` 로 검증된다.
- **FR-006**: `trailer`는 optional이며 스트리밍 종료 시 `{final: bool, transaction_id, checksum_sha256}` 를 포함한다.
- **FR-007**: 시스템은 envelope JSON Schema를 `tui/src/ipc/schema/frame.schema.json` (Draft 2020-12)에 커밋해야 하며, TypeScript 타입과 Python Pydantic v2 모델이 동일 schema에서 파생된다.
- **FR-008**: 최초 지원 frame kind 집합: `payload_start`, `payload_delta`, `payload_end`, `tool_call`, `tool_result`, `backpressure_signal`, `resume_request`, `resume_response`, `resume_rejected`, `notification_push`, `heartbeat`.
- **FR-009**: 모든 프레임은 stdout의 NDJSON 포맷 — 각 프레임은 `\n` 으로 종료되며 payload 내 `\n` 은 JSON escape (`\\n`).
- **FR-010**: 단일 프레임 직렬화 크기 > 1 MiB 이면 chunked frame 3개 이상으로 분할 전송(`trailer.final=false` 연쇄 + 마지막만 `final=true`).

**Backpressure (FR-011..FR-017)**

- **FR-011**: 백엔드는 TUI 이그레스 큐가 high-water-mark(기본 64 프레임)에 도달하면 outbound emission을 일시 중단하고 TUI drain을 대기한다.
- **FR-012**: 백엔드는 LLM 429, 부처 API 429, 내부 쿼터 포화 시 `backpressure_signal` frame을 발사한다. 페이로드는 `{kind, severity, retry_after_ms, source_agency, message_ko, message_en}`.
- **FR-013**: TUI는 `backpressure_signal` 수신 시 1 animation frame 이내 상태바 표시 + 입력을 지역 큐잉한다 (명시적 거절 아닌 부드러운 지연).
- **FR-014**: TUI 자체 ingest saturation 감지 시 `resume_pause` 프레임을 백엔드로 발사하고, drain 후 `resume_emit` 으로 재개 신호를 보낸다.
- **FR-015**: `backpressure_signal` 은 OTEL span 속성 `kosmos.ipc.backpressure.kind`·`.severity`·`.source_agency` 로 승격 기록된다.
- **FR-016**: 시스템은 backpressure 상태의 누적 시간(session-level)을 session state에 기록하여 사후 KPI 분석(시민 대기 총량) 을 가능하게 한다.
- **FR-017**: backpressure는 `disaster_alert`(CBS 재난문자) 등 `severity=critical` frame을 block 하지 않는다 (critical lane 분리).

**Reconnect handshake (FR-018..FR-025)**

- **FR-018**: TUI가 세션 재시작 시 백엔드로 `resume_request(session_id, last_seen_correlation_id, last_seen_frame_seq)` 프레임을 첫 프레임으로 전송한다.
- **FR-019**: 백엔드는 session별 in-memory ring buffer(기본 256 프레임)에 outbound 프레임을 보관하며 `.consumed` 마커 없는 프레임만 재전송 대상으로 취급한다.
- **FR-020**: `resume_request` 에 대한 응답은 `resume_response(replayed_frame_count, oldest_available_seq, session_status)` 프레임이며 이후 실제 replay 프레임을 순서대로 보낸다.
- **FR-021**: 백엔드 ring buffer 용량 초과로 특정 `last_seen_frame_seq` 이전 프레임이 소실된 경우 `resume_rejected(reason="buffer_overflow", recoverable_from_seq=N)` 프레임 반환 후 신규 세션 시작 유도.
- **FR-022**: 세션 만료 시(기본 30 분 무활동) `resume_rejected(reason="session_expired")` 반환.
- **FR-023**: 백엔드 프로세스 재시작 후의 resume은 session_id가 ring buffer를 복원할 수 없으면 `resume_rejected(reason="backend_restart")` 반환; TUI는 세션을 새로 시작한다(in-flight tool-call은 Spec 024 audit log로만 추적).
- **FR-024**: Resume 성공 시 모든 replay 프레임은 원본 `correlation_id` 와 `frame_seq` 를 유지하며, 추가 속성 `replayed=true` 는 OTEL span에만 기록(frame 본체는 원본과 byte-identical).
- **FR-025**: Resume은 최대 3회 연속 실패 시(동일 session_id로) 해당 세션을 블랙리스트에 등록하여 무한 루프 차단.

**Transaction de-dup (FR-026..FR-033)**

- **FR-026**: TUI는 `payload_start` 프레임 생성 시 `transaction_id` 를 UUIDv7로 발급하며, 재시도가 필요하면 동일 tx를 재사용해야 한다.
- **FR-027**: 백엔드는 세션별 `(transaction_id -> {result, seq})` LRU 캐시(기본 512 엔트리)를 유지하여 동일 tx 반복 도달 시 실제 tool 호출 없이 캐시된 결과를 반환한다.
- **FR-028**: `is_irreversible=true` 도구(Spec 024) 의 tx 레코드는 LRU eviction에서 제외되며 세션 종료까지 영속 저장한다.
- **FR-029**: tx cache miss 시 해당 tool 호출이 성공적으로 완료되면 결과를 캐시에 저장하고 `ToolCallAuditRecord` 에 correlation_id + transaction_id 모두 기록한다.
- **FR-030**: tx dedup은 세션 스코프 — cache 키는 `(session_id, transaction_id)` 이며 세션 경계를 넘어 공유되지 않는다.
- **FR-031**: 실패한 tool 호출(예: 부처 API 500)은 tx 캐시에 저장하지 않는다 (재시도가 다른 결과를 가져올 수 있으므로); 단, `is_irreversible` 도구가 500 반환 시에는 idempotency-key 기반 upstream 재확인 없이는 재시도를 봉쇄한다.
- **FR-032**: `transaction_id` 가 envelope에 없으면(=전통적 streaming frame) dedup 경로를 skip한다 — tx 의미론은 irreversible 작업에만 강제된다.
- **FR-033**: tx 캐시는 OTEL span 속성으로 hit/miss/stored 3가지 상태를 기록 (`kosmos.ipc.tx.cache_state`).

**Cross-cutting (FR-034..FR-040)**

- **FR-034**: 모든 frame processing은 Python `asyncio` + stdlib만 사용한다 — AGENTS.md "no new runtime deps" 하드룰 준수; LRU는 `collections.OrderedDict` 로 구현.
- **FR-035**: 프레임 파서는 malformed JSON / schema violation 시 fail-closed 하여 해당 프레임을 drop + OTEL error span을 기록한다; 전체 세션을 killing하지 않는다.
- **FR-036**: 모든 outbound frame은 stderr가 아닌 stdout으로만 송신 (Claude Agent SDK strictness 준수 — stderr는 파서 오염 금지 원칙).
- **FR-037**: 백엔드 startup 시 envelope schema 해시를 OTEL span 속성으로 emit하여 배포 버전 일관성 감사를 지원.
- **FR-038**: JSON Schema 변경 시 `version` 문자열 MUST bump; 하위 호환을 기대하지 않는다(hard cut).
- **FR-039**: heartbeat frame은 30초 간격으로 양방향 발사; 45초 무수신 시 상대 측이 dead로 간주되어 resume 시퀀스 진입.
- **FR-040**: 모든 frame envelope 구조는 `tui/src/ipc/schema/frame.schema.json` + Pydantic 모델 간 완전 동기화; CI 단계에서 Python↔TS schema 일치성 검사 수행.

### Key Entities

- **FrameEnvelope**: 단일 IPC 메시지. `{version, correlation_id, role, payload, trailer?, frame_seq, emitted_at_utc}`. NDJSON 라인 = 하나의 envelope.
- **BackpressureSignal**: 백엔드→TUI 속도 조절 신호. `{kind, severity, retry_after_ms?, source_agency, message_ko, message_en}`.
- **ResumeRequest / ResumeResponse**: 재접속 핸드셰이크 프레임 쌍. Request: `{session_id, last_seen_correlation_id?, last_seen_frame_seq?}`. Response: `{replayed_frame_count, oldest_available_seq, session_status}`.
- **TransactionRecord**: 세션 내 tx 캐시 엔트리. `{session_id, transaction_id, correlation_id, result_summary, is_irreversible, created_at_utc}`.
- **SessionRingBuffer**: 백엔드가 유지하는 최근 256개 outbound 프레임의 FIFO 큐(순환 덮어쓰기). `.consumed` 마커는 ack된 프레임 표시.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 재접속 시나리오 — TUI kill → restart → resume 소요 시간 p95 < 500 ms (in-flight 프레임 10개 이하 기준). 유실·중복·순서바뀜 프레임 0건을 `pytest-asyncio` + `bun test` 통합 검증으로 확인.
- **SC-002**: 백엔드 crash 복구 — 백엔드 프로세스 kill 후 재시작 및 client resume 시퀀스를 거쳐 대화 컨텍스트 재개까지 p95 < 3 s. 동일 tx 재시도가 실제 data.go.kr 호출로 이어지지 않음을 `ToolCallAuditRecord` 개수(=1)로 검증.
- **SC-003**: Backpressure 가시화 — 백엔드 `BackpressureSignal` 발사부터 TUI HUD 표시까지 지연 p95 < 16 ms (1 animation frame @60 Hz). 시민 대기 총량 KPI 주간 리포트 생성 가능.
- **SC-004**: Idempotency — 동일 tx 재시도 1000회 스트레스 테스트에서 `is_irreversible=true` 도구 실행은 정확히 1회, 캐시 히트 응답 반환 시간 p95 < 5 ms.
- **SC-005**: End-to-end trace — 단일 세션 tool 체인 3건에 대해 OTEL span·Langfuse trace·`ToolCallAuditRecord` 세 축에서 동일 `correlation_id` 100% 일관 검증.
- **SC-006**: Schema 일관성 — `tui/src/ipc/schema/frame.schema.json` 변경이 Python Pydantic 모델과 불일치하면 CI가 차단 (exit ≠ 0).
- **SC-007**: NDJSON 무결성 — 1000개 frame 스트림 중 malformed payload 주입 실험에서 전체 세션 중단 0건, 해당 프레임만 drop + 후속 프레임 정상 전달.
- **SC-008**: Runtime dep 증가 0건 — `pyproject.toml` 및 `tui/package.json` diff에 신규 runtime dep 추가 금지 (lint trio 기존 패턴 재사용).
- **SC-009**: Disaster-alert lane 분리 — backpressure 상태에서도 `severity=critical` frame 지연 p95 < 16 ms (회복 시 재난문자·CBS 긴급 알림 차단 방지).
- **SC-010**: 프레임 envelope JSON Schema를 외부 검증기(ajv, jsonschema)로 100개 샘플 검증 시 오탐·누락 0건.

## Assumptions

- stdio pipe는 OS 레벨에서 신뢰 가능한 순서·전달 보장을 제공한다(로컬 프로세스 간 통신). 네트워크 수준 재정렬은 고려하지 않는다.
- Session state는 in-memory only이며 프로세스 재시작 후 ring buffer 복원은 기대하지 않는다 (FR-023).
- UUIDv7 생성은 Python 3.12+ `uuid.uuid7()` 및 TUI 측 `crypto.randomUUID()` + timestamp prepend로 수행. 신규 runtime dep 도입 없음.
- `ToolCallAuditRecord` 영속화는 Spec 024 구현의 책임이며 본 스펙은 schema 연계만 담당한다.
- 세션 ID 생성·서명은 Spec 027 agent swarm 영역과 무관하지 않으나 본 스펙에서는 일반 UUIDv7 으로 충분하다.
- Ring buffer 용량(256), tx LRU 용량(512), heartbeat 간격(30 s) 은 초기값이며 `pydantic-settings` 로 env-var 조정 가능하도록 노출한다.
- `is_irreversible` 분류는 Spec 024 tool registry 메타데이터에서 상속; 본 스펙은 이 분류를 변경하지 않고 소비만 한다.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **네트워크 소켓 기반 IPC**: KOSMOS는 TUI↔backend를 동일 호스트에서 stdio로 연결한다 (AGENTS.md stack). 원격 TUI / HTTP 전송은 KOSMOS 아키텍처 전제가 아님.
- **Cross-session tx 공유**: `transaction_id` 는 세션 스코프이며 세션 경계를 넘는 dedup은 audit 원장(Spec 024)의 책임이다.
- **프레임 비동기 확인(ack) 의 배치 압축**: 매 frame별 ack를 1-to-1 유지 — 단순성·진단성 우선.
- **디스크 영속 ring buffer**: 프로세스 재시작 시 복원 대상 아님 (FR-023, 감사 로그로만 이력 유지).
- **Frame 압축 (gzip/brotli)**: stdio는 로컬이므로 불필요. 대용량 payload는 chunked frame(FR-010) 로 해결.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| 원격 TUI(WebSocket/HTTP) 전송 계층 | AX 배포 후 공무원 원격 상담 수요 발생 시 재검토 | Phase 3 remote ops | NEEDS TRACKING |
| Frame-level 서명/암호화(e2e) | stdio 로컬 전제, 외부 노출 없음; 필요 시 Spec 024 Merkle chain 확장 | Phase 3 sovereignty | NEEDS TRACKING |
| 백엔드 다중 인스턴스 세션 shard | 현 단계 단일 백엔드 모델; swarm 수평 확장 시 재설계 | Phase 2.5 swarm shard | NEEDS TRACKING |
| WebMCP-style declarative capability advertisement | MCP transports 표준 정립 대기 | Phase 2.5 MCP host | NEEDS TRACKING |
| OS-native stdio alternative(Windows named pipes) | 타겟 OS는 macOS/Linux; 우선순위 낮음 | Phase 3 portability | NEEDS TRACKING |

## References

- **ADR**: `docs/adr/ADR-006-cc-migration-vision-update.md` § Part D-2 Epic A
- **Vision**: `docs/vision.md` § L1 Transport layer + § L5 TUI layer + Reference materials
- **Existing specs**:
  - Spec 021 OTEL GenAI instrumentation — correlation_id 승격 소스
  - Spec 024 Tool Template Security v1 — `ToolCallAuditRecord` 연계
  - Spec 025 Tool Template Security v6 — `is_irreversible` 분류
  - Spec 027 Agent Swarm Core — mailbox `.consumed` 마커 패턴 재활용
  - Spec 031 Five-primitive harness — `subscribe` primitive의 backpressure/resume 경로 연결
- **External reference materials** (researched 2026-04-19):
  - CC sourcemap `src/services/api/{client,bootstrap,sessionIngress,withRetry}.ts` — HTTP 기반이지만 retry+correlation 패턴 포팅 대상
  - CC sourcemap `src/session/` — session lifecycle + 복구 패턴
  - MCP Transports Spec 2025-03-26 — Last-Event-ID semantic (SSE), resume 설계 기준
  - LSP 3.17 base protocol — JSON-RPC id correlation, 구조화된 envelope 선례
  - Claude Agent SDK docs — stdio strictness(stderr 오염 금지)
  - Node.js Streams doc — backpressure + highWaterMark 기본 개념
  - NDJSON spec (ndjson.org) — 라인 분리 JSON 포맷 표준
  - Idempotency key 3-step approach (Stripe engineering blog 2017 + Shopify idempotency-key RFC draft) — UUID + transactional state + stale reclaim
- **AGENTS.md hard rules**: "no new runtime deps" (SC-008), stdlib `logging` only, Pydantic v2 for all tool I/O.
- **Memory**: `project_tui_architecture.md`, `feedback_harness_not_reimplementation.md` — CC 포트 + 표면 역공학 원칙.
