# Phase 1 Data Model — Spec 031 Five-Primitive Harness

**Branch**: `031-five-primitive-harness` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

> All models are **Pydantic v2**. `Any` is forbidden (Constitution §III). Every I/O schema is declared below; each primitive's contract JSON schema is exported under `contracts/`.

---

## Convention

- `Literal[...]` enums are **closed**; adding a value is a spec amendment (Edge Case gate).
- Discriminated unions use `Field(discriminator=...)`.
- Fields named `params` on the main surface are deliberately `dict[str, object]`-shaped; the *adapter* owns the typed Pydantic model and validates at invocation time. This matches Pydantic AI's per-adapter schema pattern and is Constitution-compliant because `dict[str, object]` is not `Any`.
- All timestamps are RFC 3339 with timezone; skew tolerance ±300s matches Spec 024 invariant I4.

---

## 1. `SubmitEnvelope` (main surface — `submit`)

```python
class SubmitInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tool_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_]*$")
    params: dict[str, object] = Field(default_factory=dict)

class SubmitStatus(StrEnum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    rejected = "rejected"

class SubmitOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    transaction_id: str = Field(min_length=1, max_length=128)
    status: SubmitStatus
    adapter_receipt: dict[str, object] = Field(default_factory=dict)
```

**Invariants** (enforced by `@model_validator(mode="after")` + `ToolRegistry.register()` backstop):
- `SubmitInput.tool_id` MUST exist in the registry at invocation time; `AdapterNotFoundError` structured result otherwise.
- `SubmitOutput.transaction_id` MUST be deterministic per invocation (content-hash of input + adapter-declared nonce).
- `SubmitInput` and `SubmitOutput` MUST NOT contain any of the banned strings from SC-002: `check_eligibility`, `reserve_slot`, `subscribe_alert`, `pay`, `issue_certificate`, `submit_application`, `declared_income_krw`, `certificate_type`, `family_register`, `resident_register`. Enforced by a model-tree-scan in `tests/test_submit_banned_words.py`.
- Failed adapter invocations MUST surface as `status=failed|rejected` + `adapter_receipt` carrying the structured error; never as an unhandled Python exception (FR-005).

---

## 2. `AuthContext` (discriminated union — output of `verify`)

```python
PublishedTier = Literal[
    # gongdong_injeungseo — 3 labels
    "gongdong_injeungseo_personal_aal3",
    "gongdong_injeungseo_corporate_aal3",
    "gongdong_injeungseo_bank_only_aal2",
    # geumyung_injeungseo — 2 labels
    "geumyung_injeungseo_personal_aal2",
    "geumyung_injeungseo_business_aal3",
    # ganpyeon_injeung — 7 labels
    "ganpyeon_injeung_pass_aal2",
    "ganpyeon_injeung_kakao_aal2",
    "ganpyeon_injeung_naver_aal2",
    "ganpyeon_injeung_toss_aal2",
    "ganpyeon_injeung_bank_aal2",
    "ganpyeon_injeung_samsung_aal2",
    "ganpyeon_injeung_payco_aal2",
    # digital_onepass — 3 labels
    "digital_onepass_level1_aal1",
    "digital_onepass_level2_aal2",
    "digital_onepass_level3_aal3",
    # mobile_id — 2 labels
    "mobile_id_mdl_aal2",
    "mobile_id_resident_aal2",
    # mydata — 1 label
    "mydata_individual_aal2",
]  # Total: 18

NistAalHint = Literal["AAL1", "AAL2", "AAL3"]

class VerifyInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    family_hint: Literal[
        "gongdong_injeungseo", "geumyung_injeungseo", "ganpyeon_injeung",
        "digital_onepass", "mobile_id", "mydata",
    ]
    session_context: dict[str, object] = Field(default_factory=dict)

class _AuthContextBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    published_tier: PublishedTier       # primary axis
    nist_aal_hint: NistAalHint           # advisory secondary axis
    verified_at: datetime                # RFC 3339
    external_session_ref: str | None     # opaque reference to external provider

class GongdongInjeungseoContext(_AuthContextBase):
    family: Literal["gongdong_injeungseo"] = "gongdong_injeungseo"
    certificate_issuer: str              # e.g. "KICA"
    # published_tier narrowed to 3 gongdong labels at validation

class GeumyungInjeungseoContext(_AuthContextBase):
    family: Literal["geumyung_injeungseo"] = "geumyung_injeungseo"
    bank_cluster: Literal["kftc"]        # 금융결제원 클라우드

class GanpyeonInjeungContext(_AuthContextBase):
    family: Literal["ganpyeon_injeung"] = "ganpyeon_injeung"
    provider: Literal["pass", "kakao", "naver", "toss", "bank", "samsung", "payco"]

class DigitalOnepassContext(_AuthContextBase):
    family: Literal["digital_onepass"] = "digital_onepass"
    level: Literal[1, 2, 3]

class MobileIdContext(_AuthContextBase):
    family: Literal["mobile_id"] = "mobile_id"
    id_type: Literal["mdl", "resident"]  # 모바일운전면허 | 모바일주민등록증

class MyDataContext(_AuthContextBase):
    family: Literal["mydata"] = "mydata"
    provider_id: str                     # 마이데이터 사업자 코드

AuthContext = Annotated[
    GongdongInjeungseoContext | GeumyungInjeungseoContext | GanpyeonInjeungContext
    | DigitalOnepassContext | MobileIdContext | MyDataContext,
    Field(discriminator="family"),
]

class VerifyMismatchError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    family: Literal["mismatch_error"]  # structural discriminator — enables Field(discriminator="family") on VerifyOutput.result
    reason: Literal["family_mismatch"]
    expected_family: str
    observed_family: str
    message: str

class VerifyOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    result: AuthContext | VerifyMismatchError = Field(discriminator="family")  # see §2.1
```

> **Discriminator note**: `VerifyMismatchError.family = "mismatch_error"` is a **structural discriminator**, not a family-of-identity. It is the seventh tag value on the `Field(discriminator="family")` union so that Pydantic v2 can dispatch between the six real `AuthContext` variants and the error variant in a single declarative union. This label is reserved — no real identity family may use `"mismatch_error"`.

### 2.1 Per-family `published_tier` narrowing

Each family variant MUST validate that its `published_tier` belongs to the family's subset (FR-007 combined with the edge case "value not in the 18-label enum"). Enforced by `@model_validator(mode="after")` on each variant class:

| Variant | Allowed `published_tier` values |
|---|---|
| `GongdongInjeungseoContext` | `gongdong_injeungseo_{personal,corporate}_aal3`, `gongdong_injeungseo_bank_only_aal2` |
| `GeumyungInjeungseoContext` | `geumyung_injeungseo_{personal_aal2,business_aal3}` |
| `GanpyeonInjeungContext` | `ganpyeon_injeung_{pass,kakao,naver,toss,bank,samsung,payco}_aal2` |
| `DigitalOnepassContext` | `digital_onepass_level{1_aal1,2_aal2,3_aal3}` |
| `MobileIdContext` | `mobile_id_{mdl,resident}_aal2` |
| `MyDataContext` | `mydata_individual_aal2` |

**Coercion prohibited** (FR-010): `family_hint` mismatch produces `VerifyMismatchError`, never silent coercion.

**Delegation-only** (FR-009): none of the variants hold private keys; `external_session_ref` is an opaque handle given by the relevant external operator.

---

## 3. `SubscriptionEvent` (discriminated on `kind` — output of `subscribe`)

```python
class SubscribeInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tool_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_]*$")
    params: dict[str, object] = Field(default_factory=dict)
    lifetime: timedelta                          # Duration — bounded lifetime required
    # webhook_url field deliberately absent (FR-013)

class CbsBroadcastEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["cbs_broadcast"] = "cbs_broadcast"
    cbs_message_id: Literal[4370, 4371, 4372, 4373, 4374, 4375, 4376, 4377,
                             4378, 4379, 4380, 4381, 4382, 4383, 4384, 4385]
    received_at: datetime
    payload_hash: str                            # sha256 of raw bearer payload
    language: Literal["ko", "en"]
    body: str

class RestPullTickEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["rest_pull_tick"] = "rest_pull_tick"
    tool_id: str
    tick_at: datetime
    response_hash: str                           # sha256 of the REST response
    payload: dict[str, object]

class RssItemEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["rss_item"] = "rss_item"
    feed_tool_id: str
    guid: str                                    # RSS 2.0 <guid>
    published_at: datetime | None
    title: str
    link: str | None
    description: str | None

SubscriptionEvent = Annotated[
    CbsBroadcastEvent | RestPullTickEvent | RssItemEvent,
    Field(discriminator="kind"),
]

class SubscriptionHandle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    subscription_id: str
    tool_id: str
    opened_at: datetime
    closes_at: datetime                          # opened_at + lifetime
```

**Invariants**:
- `lifetime` MUST be bounded; `timedelta(days=365)` is an enforced ceiling (FR-011, Edge Case "lifetime exhaustion mid-event").
- No field in `SubscribeInput` accepts a URL that could act as an inbound receiver (FR-013).
- RSS `guid` de-duplication is stateful *within a subscription*; reset `guid`s on publisher side surface as new items (Edge Case ratified in §4 of research).

---

## 4. `AdapterRegistration` (registry metadata)

```python
class AdapterPrimitive(StrEnum):
    lookup = "lookup"
    resolve_location = "resolve_location"
    submit = "submit"
    subscribe = "subscribe"
    verify = "verify"

class AdapterSourceMode(StrEnum):
    OPENAPI = "OPENAPI"          # byte-mirrored from a public OpenAPI spec
    OOS = "OOS"                  # shape-mirrored from an open-source SDK / impl
    HARNESS_ONLY = "harness-only"  # net-new, no external byte/shape mirror

class AdapterRegistration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tool_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_]*$")
    primitive: AdapterPrimitive
    module_path: str             # e.g. "kosmos.tools.mock.data_go_kr.fines_pay"
    input_model_ref: str         # dotted ref to adapter's Pydantic input model
    source_mode: AdapterSourceMode

    # Spec 031 §6 (v1.2 dual-axis) — both required at or after v1.2 GA (FR-030)
    published_tier_minimum: PublishedTier | None = None
    nist_aal_hint: NistAalHint | None = None

    # Spec 024 / 025 invariants preserved (FR-028)
    requires_auth: bool = True            # fail-closed default (Constitution §II)
    is_personal_data: bool = True         # fail-closed default
    is_concurrency_safe: bool = False     # fail-closed default
    cache_ttl_seconds: int = 0            # fail-closed default
    rate_limit_per_minute: int = 10
    search_hint: dict[Literal["ko", "en"], list[str]] = Field(default_factory=dict)
    # Spec 024 extensions
    auth_type: Literal["public", "api_key", "oauth"]
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]
    pipa_class: Literal["non_personal", "personal_standard", "personal_sensitive", "personal_unique_id"]
    is_irreversible: bool = False
    dpa_reference: str | None = None
```

**Invariants** (preserved from Spec 024 V1–V4 + Spec 025 V6):
- V1: `primitive=submit` ∧ `pipa_class ∈ {personal_*}` → `is_irreversible=True` unless explicit audit-preservation contract.
- V3: `auth_level` MUST match the canonical `_AUTH_TYPE_LEVEL_MAPPING` (Spec 025).
- V6: `(auth_type, auth_level)` MUST ∈ `{public⇒{public, AAL1}, api_key⇒{AAL1, AAL2, AAL3}, oauth⇒{AAL1, AAL2, AAL3}}`.
- FR-020: `tool_id` collision at registration time → structured error, first-wins.
- FR-038 (PII invariant, preserved from existing `registry.py`): `is_personal_data=True` → `requires_auth=True` ∧ `auth_level ≠ "public"`.
- **v1.2 GA window** (FR-027/030): after v1.2 GA, `published_tier_minimum` and `nist_aal_hint` MUST both be non-None; pre-v1.2 shipped contracts keep the None default during the compatibility window.

---

## 5. `ScenarioEntry` + `MockSystemRoot` (docs-layer entities)

These are filesystem shapes, not runtime Pydantic models, but they are enforced by docs-lint tests:

```
docs/mock/<system>/
├── README.md                 # public-spec URL, license, mirror axis (byte|shape)
├── fixtures/                 # recorded fixtures
└── adapters/                 # stub pointing at src/kosmos/tools/mock/<ministry>/*.py

docs/scenarios/<journey>.md   # includes an explicit "KOSMOS ↔ real system" handoff heading
```

**Invariants** (docs-lint, exercised by `tests/test_mock_scenario_split.py`):
- `docs/mock/` contains **exactly 6** subdirectories: `data_go_kr`, `omnione`, `barocert`, `mydata`, `npki_crypto`, `cbs` (FR-021, SC-004).
- `docs/scenarios/` contains **exactly 3** `.md` files documenting OPAQUE journeys (FR-023, SC-004). Each file MUST contain the handoff heading (FR-024).
- No adapter under `src/kosmos/tools/mock/` may implement an OPAQUE system (FR-026). Enforced by grep over adapter modules vs the scenario list.

---

## 6. Entity relationships

```
┌────────────────────┐        register        ┌────────────────────────┐
│ AdapterRegistration │◀──────────────────────│ ToolRegistry (singleton)│
└─────────┬──────────┘                        └────────────┬───────────┘
          │                                                │
          │ dispatched by tool_id                          │ exposes 5 primitives
          ▼                                                ▼
┌────────────────────┐                       ┌────────────────────────┐
│ <adapter>.invoke() │                       │ SubmitInput / SubmitOutput
└─────────┬──────────┘                       │ LookupInput / LookupOutput
          │                                  │ ResolveLocationInput/Output
          │ produces                         │ SubscribeInput / SubscriptionHandle
          ▼                                  │ VerifyInput / VerifyOutput
  SubmitOutput |                             └────────────────────────┘
  AuthContext  |
  AsyncIterator[SubscriptionEvent] |
  LookupOutput | ResolveLocationOutput
          │
          │ audited
          ▼
  ToolCallAuditRecord (Spec 024 v1, preserved I1–I5)
```

---

## 7. Error model

All primitives return structured errors (never raw exceptions) per FR-005 and the general harness principle. Error shapes reuse Spec 022's `LookupError` idiom:

```python
class AdapterNotFoundError(BaseModel):
    reason: Literal["adapter_not_found"] = "adapter_not_found"
    tool_id: str
    message: str

class AdapterInvocationError(BaseModel):
    reason: Literal["adapter_invocation_failed"] = "adapter_invocation_failed"
    tool_id: str
    structured: dict[str, object]   # adapter-specific structured error
    message: str

class SubscriptionBackpressureDrop(BaseModel):
    reason: Literal["subscription_backpressure_drop"] = "subscription_backpressure_drop"
    subscription_id: str
    events_dropped: int
    message: str
```

All structured errors carry `meta = {source, fetched_at, request_id, elapsed_ms}` per the `envelope.normalize` contract (existing from Spec 022).
