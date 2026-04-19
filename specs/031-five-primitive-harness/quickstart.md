# Spec 031 — Five-Primitive Harness Quickstart

**Branch**: `031-five-primitive-harness` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md)

This quickstart is for contributors touching the main tool surface. Goal: a fresh contributor maps each of the 5 primitives to its Claude Code analogue in under 5 minutes (SC-009) and registers a mock adapter against any primitive in under 30 minutes.

---

## 1. Mental model

KOSMOS migrates the Claude Code harness (tool loop + permission + context + TUI) from the developer domain to the Korean public-service domain. The main surface declares **shape**; adapters own **domain**.

| KOSMOS primitive | Claude Code analogue | Harness verb |
|---|---|---|
| `lookup` (mode=search / fetch) | `Grep` + `Read` + `WebFetch` | search + fetch on tool registry |
| `resolve_location` | `Glob` | address → coordinate / admin-code |
| `submit` | `Bash` | side-effect write |
| `subscribe` | *no direct CC analog* | passive multi-modality stream |
| `verify` | *no direct CC analog* | external auth delegation |

See [data-model.md](./data-model.md) for the full Pydantic v2 shapes and [research.md](./research.md) §1 for the reference-mapping to `restored-src/src/tools/` and `restored-src/src/services/`.

---

## 2. Directory layout

```
src/kosmos/tools/
├── <ministry>/                  # real adapters (e.g. koroad/, hira/, nmc/)
│   └── <adapter>.py
└── mock/
    └── <ministry>/              # mock adapters mirroring 6 mirror-able systems
        └── <adapter>.py

docs/mock/                       # exactly 6 subdirs (SC-004)
├── data_go_kr/
├── omnione/
├── barocert/
├── mydata/
├── npki_crypto/
└── cbs/
    ├── README.md                # public-spec URL + license + mirror axis
    ├── fixtures/                # recorded fixtures (PyPinkSign, 3GPP TS 23.041, etc.)
    └── adapters/                # stub pointing at src/kosmos/tools/mock/...

docs/scenarios/                  # exactly 3 OPAQUE journeys (SC-004)
├── gov24_submission.md          # 정부24 민원 제출
├── kec_xml_signature.md         # KEC 전자세금계산서 서명부
└── npki_portal_session.md       # NPKI 포털별 challenge-response
```

---

## 3. Registering an adapter (worked example)

Register a mock `submit` adapter for a traffic-fine payment (`mock_traffic_fine_pay_v1`):

```python
# src/kosmos/tools/mock/data_go_kr/fines_pay.py
from pydantic import BaseModel, ConfigDict, Field
from kosmos.tools.registry import ToolRegistry, AdapterRegistration, AdapterPrimitive
from kosmos.primitives.submit import SubmitOutput, SubmitStatus

class FinesPayParams(BaseModel):
    """Adapter-typed params. Ministry enum lives HERE, not on main surface."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    fine_reference: str = Field(min_length=1, max_length=32)
    payment_method: Literal["virtual_account", "card", "bank_transfer"]

async def invoke(params: FinesPayParams) -> SubmitOutput:
    # ... call mock fixture, compute deterministic transaction_id ...
    return SubmitOutput(
        transaction_id=f"mock-{sha256(...)}",
        status=SubmitStatus.succeeded,
        adapter_receipt={"접수번호": "2026-04-19-0001"},
    )

REGISTRATION = AdapterRegistration(
    tool_id="mock_traffic_fine_pay_v1",
    primitive=AdapterPrimitive.submit,
    module_path=__name__,
    input_model_ref=f"{__name__}.FinesPayParams",
    source_mode="OOS",
    published_tier_minimum="ganpyeon_injeung_kakao_aal2",  # v1.2 required
    nist_aal_hint="AAL2",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["과태료", "교통범칙금", "납부"],
        "en": ["traffic fine", "payment"],
    },
    auth_type="oauth",
    auth_level="AAL2",
    pipa_class="personal_standard",
    is_irreversible=True,  # V1 invariant: submit + personal_* → irreversible
)
ToolRegistry.register(REGISTRATION)
```

The main-surface call is always **shape-only**:

```python
result = await kosmos.submit(
    tool_id="mock_traffic_fine_pay_v1",
    params={"fine_reference": "2026-04-19-0001", "payment_method": "virtual_account"},
)
# result: SubmitOutput(transaction_id=..., status=..., adapter_receipt=...)
```

No domain-specific field ever appears on `SubmitInput` / `SubmitOutput` (SC-002).

---

## 4. Calling each primitive (one-liner cheat-sheet)

```python
# lookup (preserved byte-identical from Spec 022)
await kosmos.lookup(mode="search", query="교통사고 다발지역", top_k=5)
await kosmos.lookup(mode="fetch", tool_id="koroad_accident_hazard_search", params={...})

# resolve_location (preserved byte-identical from Spec 022)
await kosmos.resolve_location(query="서울시 종로구 세종대로 209")

# submit (new — FR-001..005)
await kosmos.submit(tool_id="mock_traffic_fine_pay_v1", params={...})

# subscribe (new — FR-011..015, AsyncIterator; no webhook URL accepted)
async for event in kosmos.subscribe(
    tool_id="mock_cbs_disaster_v1", params={"region": "서울"}, lifetime_seconds=3600,
):
    ...  # event: CbsBroadcastEvent | RestPullTickEvent | RssItemEvent | SubscriptionBackpressureDrop

# verify (new — FR-006..010; delegation-only, no CA / HSM / VC issuer)
auth_ctx = await kosmos.verify(family_hint="ganpyeon_injeung", session_context={...})
# auth_ctx: discriminated on `family`, carries published_tier + nist_aal_hint
```

---

## 5. Smoke-test checklist (post-merge)

Run in order, first failure is a ship-stopper:

```bash
# SC-001: tool count = 5
uv run pytest tests/unit/primitives/test_registry_count.py -q

# SC-002: submit envelope contains zero banned strings
uv run pytest tests/test_submit_banned_words.py -q

# SC-003: Spec 022 green, unchanged
uv run pytest specs/022-mvp-main-tool/tests/ -q

# SC-004: docs/mock/ = 6 subdirs, docs/scenarios/ = 3 journeys
uv run pytest tests/test_mock_scenario_split.py -q

# SC-005: published_tier-based branching works end-to-end
uv run pytest tests/integration/test_submit_published_tier_gate.py -q

# SC-006: no private keys / CA material
grep -r "BEGIN PRIVATE KEY\|BEGIN RSA PRIVATE KEY" src/ docs/ | grep -v ".mock-fixture"

# SC-007: v1.2 registrations declare both axes
uv run pytest tests/unit/security/test_v12_dual_axis.py -q

# SC-008: no new runtime dependency
git diff main -- pyproject.toml

# SC-010: 8-verb regression lint
uv run pytest tests/lint/test_no_legacy_verbs.py -q
```

---

## 6. When to escalate from mock → scenario

An OPAQUE system (정부24 submission / KEC XML 서명부 / NPKI 포털 세션) MUST remain a scenario doc *even if* you find an open-source reverse-engineered fork. The test of "mock-eligibility" is:

1. Public OpenAPI / SDK / XSD / 3GPP / ECMA / Apache-2.0 reference impl exists **AND**
2. License permits fixture recording for test use

Fail either → `docs/scenarios/<journey>.md` only. When an institutional disclosure flips (1) to true, follow the scenario→mock promotion path (FR-025).

---

## 7. Further reading

- [spec.md](./spec.md) — full FR / SC / edge cases (257 lines)
- [research.md](./research.md) — reference map to `restored-src/`, 18-label ratification, mock/scenario split rationale
- [data-model.md](./data-model.md) — Pydantic v2 schemas for all five primitives + registry
- [contracts/](./contracts/) — JSON Schema Draft 2020-12 exports
- [`AGENTS.md`](../../AGENTS.md) — project-wide hard rules
- [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — Constitution §I–VI
