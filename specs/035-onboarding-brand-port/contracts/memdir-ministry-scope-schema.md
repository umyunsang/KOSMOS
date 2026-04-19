# Contract: Memdir ministry-scope schema + main-tool router guard

**Feature**: Epic H #1302
**Phase**: 1
**Owner of authoritative source**: `src/kosmos/memdir/ministry_scope.py` + `src/kosmos/tools/main_router.py`
**Storage root**: `~/.kosmos/memdir/user/ministry-scope/`
**Main-tool reference**: `specs/022-mvp-main-tool/`
**PIPA role reference**: project memory `project_pipa_role.md` — KOSMOS = PIPA § 26 수탁자 (processor) by default

This contract specifies the ministry-scope acknowledgment schema AND the router-level guard that enforces opt-out at the pre-network boundary.

---

## § 1 · JSON schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "kosmos.memdir.user.ministry-scope/1",
  "title": "MinistryScopeAcknowledgment",
  "type": "object",
  "additionalProperties": false,
  "required": ["scope_version", "timestamp", "session_id", "ministries", "schema_version"],
  "properties": {
    "scope_version": {
      "type": "string",
      "pattern": "^v\\d+$"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "session_id": {
      "type": "string",
      "format": "uuid"
    },
    "ministries": {
      "type": "array",
      "minItems": 4,
      "maxItems": 4,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ministry_code", "opt_in"],
        "properties": {
          "ministry_code": {
            "type": "string",
            "enum": ["KOROAD", "KMA", "HIRA", "NMC"]
          },
          "opt_in": { "type": "boolean" }
        }
      }
    },
    "schema_version": {
      "type": "string",
      "const": "1"
    }
  }
}
```

---

## § 2 · Pydantic v2 stub

```python
# src/kosmos/memdir/ministry_scope.py
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


MinistryCode = Literal["KOROAD", "KMA", "HIRA", "NMC"]


class MinistryOptIn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ministry_code: MinistryCode
    opt_in: bool


class MinistryScopeAcknowledgment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    scope_version: str = Field(pattern=r"^v\d+$")
    timestamp: datetime
    session_id: UUID
    ministries: frozenset[MinistryOptIn]
    schema_version: Literal["1"] = "1"

    @model_validator(mode="after")
    def _check_four_unique(self) -> "MinistryScopeAcknowledgment":
        codes = {m.ministry_code for m in self.ministries}
        expected = {"KOROAD", "KMA", "HIRA", "NMC"}
        if codes != expected:
            raise ValueError(f"ministries must cover {expected}, got {codes}")
        return self
```

---

## § 3 · Zod mirror

```typescript
// tui/src/memdir/ministry-scope.ts
import { z } from "zod"

export const MinistryOptInSchema = z.object({
  ministry_code: z.enum(["KOROAD", "KMA", "HIRA", "NMC"]),
  opt_in: z.boolean(),
})

export const MinistryScopeAcknowledgmentSchema = z.object({
  scope_version: z.string().regex(/^v\d+$/),
  timestamp: z.string().datetime({ offset: false }),
  session_id: z.string().uuid(),
  ministries: z.array(MinistryOptInSchema).length(4)
    .refine(arr => new Set(arr.map(m => m.ministry_code)).size === 4,
            { message: "ministries must have 4 unique codes" })
    .refine(arr => {
      const codes = new Set(arr.map(m => m.ministry_code))
      return ["KOROAD", "KMA", "HIRA", "NMC"].every(c => codes.has(c))
    }, { message: "ministries must cover {KOROAD, KMA, HIRA, NMC}" }),
  schema_version: z.literal("1"),
})

export type MinistryScopeAcknowledgment = z.infer<typeof MinistryScopeAcknowledgmentSchema>
```

---

## § 4 · Storage layout

```
~/.kosmos/memdir/user/ministry-scope/
├── 2026-04-20T14-33-17Z-018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60.json
└── ...
```

Same append-only + atomic-write semantics as `contracts/memdir-consent-schema.md § 4`. "Latest effective state" = sort by filename descending, take first match with `scope_version === CURRENT_SCOPE_VERSION`.

---

## § 5 · Main-tool router guard

`specs/022-mvp-main-tool/` defines `MainToolRouter.resolve(tool_id, params)`. Epic H extends it with the ministry-scope guard:

```python
# src/kosmos/tools/main_router.py  (extension)
from kosmos.memdir.ministry_scope import latest_scope

MINISTRY_TOOL_PREFIX: dict[str, MinistryCode] = {
    "koroad_": "KOROAD",
    "kma_": "KMA",
    "hira_": "HIRA",
    "nmc_": "NMC",
}


def _ministry_for_tool(tool_id: str) -> MinistryCode | None:
    for prefix, code in MINISTRY_TOOL_PREFIX.items():
        if tool_id.startswith(prefix):
            return code
    return None


def resolve_with_scope_guard(tool_id: str, params: dict, memdir_root: Path):
    ministry = _ministry_for_tool(tool_id)
    if ministry is None:
        return resolve(tool_id, params)  # no ministry guard for non-ministry tools

    scope = latest_scope(memdir_root / "user" / "ministry-scope")
    if scope is None or not _opt_in(scope, ministry):
        raise MinistryOptOutRefusal(
            ministry=ministry,
            message=f"{_ministry_korean_name(ministry)}의 데이터 사용에 동의하지 않으셨습니다. "
                    f"다시 온보딩을 실행하시려면 세션을 종료하고 재시작하십시오.",
        )
    return resolve(tool_id, params)
```

**Refusal contract**:

- `MinistryOptOutRefusal` is a Pydantic-typed exception with `ministry: MinistryCode` and `message: str` (Korean citizen-facing).
- The exception is raised **before** any network call (SC-009 < 100 ms requirement).
- The TUI catches `MinistryOptOutRefusal` and renders the Korean message in an error-styled message row; the session remains open (the citizen may issue other queries).

**Ministry-to-prefix mapping**: derived from Spec 022's tool-registration convention — every adapter in `src/kosmos/tools/adapters/` declares its ministry at registration time. The `MINISTRY_TOOL_PREFIX` constant here is the static derivation of those declarations; a CI check ensures the constant stays in sync.

---

## § 6 · Korean ministry names

Used in § 5 refusal messages and in `MinistryScopeStep.tsx` ministry-list UI:

| MinistryCode | Korean name | English adapter code |
|---|---|---|
| KOROAD | 한국도로공사 | KOROAD |
| KMA | 기상청 | KMA |
| HIRA | 건강보험심사평가원 | HIRA |
| NMC | 국립중앙의료원 | NMC |

Per research R-9, citizen-facing UI uses the pattern `<Korean name> (<English code>)` to ensure screen-reader disambiguation.

---

## § 7 · Traceability

| Clause | Spec FR | Data-model I# | Test |
|---|---|---|---|
| § 1 JSON schema | FR-016 | I-13, I-14 | `test_ministry_scope.py::test_schema_roundtrip` |
| § 2 Pydantic stub | FR-016 | I-13, I-14 | same + `_check_four_unique` validator |
| § 3 Zod mirror | FR-016 | I-13, I-14 | `ministry-scope.zod.test.ts` |
| § 4 storage | FR-016 | I-15 | `test_ministry_scope.py::test_append_only` |
| § 5 router guard | FR-016, SC-009 | X-3 | `test_main_router.py::test_opt_out_refusal` (< 100 ms budget) |
| § 6 Korean names | R-9 | I-23 | refusal-message snapshot test |
