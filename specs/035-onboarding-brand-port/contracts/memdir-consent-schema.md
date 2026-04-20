# Contract: Memdir PIPA consent schema

**Feature**: Epic H #1302
**Phase**: 1
**Owner of authoritative source**: `src/kosmos/memdir/user_consent.py` (Pydantic v2) + `tui/src/memdir/consent.ts` (Zod mirror)
**Storage root**: `~/.kosmos/memdir/user/consent/`
**PIPA reference**: 개인정보 보호법 § 22 (수집·이용 동의) + § 24 (고유식별정보 처리); KOSMOS as PIPA § 26 수탁자 per project memory

This contract specifies the JSON record schema, directory layout, and write semantics for `PIPAConsentRecord`.

---

## § 1 · JSON schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "kosmos.memdir.user.consent/1",
  "title": "PIPAConsentRecord",
  "type": "object",
  "additionalProperties": false,
  "required": ["consent_version", "timestamp", "aal_gate", "session_id", "citizen_confirmed", "schema_version"],
  "properties": {
    "consent_version": {
      "type": "string",
      "pattern": "^v\\d+$"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC with trailing Z"
    },
    "aal_gate": {
      "type": "string",
      "enum": ["AAL1", "AAL2", "AAL3"]
    },
    "session_id": {
      "type": "string",
      "format": "uuid"
    },
    "citizen_confirmed": {
      "type": "boolean",
      "const": true
    },
    "schema_version": {
      "type": "string",
      "const": "1"
    }
  }
}
```

**Notes**:

- `citizen_confirmed` is `const: true` — a record MUST never be written for a decline (declines terminate the session per FR-014 and `contracts/onboarding-step-registry.md § 2`).
- `aal_gate` enum values come from `specs/033-permission-v2-spectrum/` (research R-5). Adding a new value requires a Spec 033 amendment.
- `schema_version` is bumped only via ADR amendment; the reader rejects any record with a schema_version it does not recognise.

---

## § 2 · Pydantic v2 stub (Python)

```python
# src/kosmos/memdir/user_consent.py
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from kosmos.permissions import AuthenticatorAssuranceLevel  # Spec 033


class PIPAConsentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    consent_version: str = Field(pattern=r"^v\d+$")
    timestamp: datetime  # MUST be tz-aware UTC
    aal_gate: AuthenticatorAssuranceLevel
    session_id: UUID  # UUIDv7 per Spec 032
    citizen_confirmed: Literal[True]
    schema_version: Literal["1"] = "1"
```

---

## § 3 · Zod mirror (TypeScript)

```typescript
// tui/src/memdir/consent.ts
import { z } from "zod"

export const PIPAConsentRecordSchema = z.object({
  consent_version: z.string().regex(/^v\d+$/),
  timestamp: z.string().datetime({ offset: false }),
  aal_gate: z.enum(["AAL1", "AAL2", "AAL3"]),
  session_id: z.string().uuid(),
  citizen_confirmed: z.literal(true),
  schema_version: z.literal("1"),
})

export type PIPAConsentRecord = z.infer<typeof PIPAConsentRecordSchema>
```

---

## § 4 · Storage layout

```
~/.kosmos/memdir/user/consent/
├── 2026-04-20T14-32-05Z-018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60.json
├── 2026-04-25T09-11-42Z-018f9123-abc4-7bef-8d1e-1a2b3c4d5e6f.json   ← consent version bump writes new file
└── ...
```

**File-name pattern**: `<iso8601-utc-colons-replaced-with-dashes>-<session_uuidv7>.json`.

**Append-only**: never overwrite, never delete. "Latest effective consent" = sort by filename descending, take first match with `consent_version === CURRENT_CONSENT_VERSION`.

**Atomic write** (Spec 027 § 4 pattern):

```python
# pseudo-code
tmp = final_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(record.model_dump(mode="json")))
os.fsync(tmp.open("rb").fileno())
os.rename(tmp, final_path)
```

---

## § 5 · Reader contract

```python
# src/kosmos/memdir/user_consent.py
def latest_consent(base: Path) -> PIPAConsentRecord | None:
    """Return the most recent PIPAConsentRecord, or None if no record exists."""
    candidates = sorted(base.glob("*.json"), reverse=True)
    for path in candidates:
        try:
            return PIPAConsentRecord.model_validate_json(path.read_text())
        except ValidationError:
            continue  # skip corrupt records; do NOT repair
    return None
```

**TypeScript reader** (same semantics via `PIPAConsentRecordSchema.safeParse`).

**Invariant**: if `latest_consent()` returns `None` OR a record whose `consent_version !== CURRENT_CONSENT_VERSION`, the onboarding state machine renders the full 3-step flow (per `contracts/onboarding-step-registry.md § 3`).

---

## § 6 · Traceability

| Clause | Spec FR | Data-model I# | Test |
|---|---|---|---|
| § 1 JSON schema | FR-013 | I-9 | `test_user_consent.py::test_schema_roundtrip` |
| § 2 Pydantic stub | FR-013 | I-9 | same |
| § 3 Zod mirror | FR-013 | I-9 | `consent.zod.test.ts` |
| § 4 storage layout | FR-013 | I-10, I-11 | `test_user_consent.py::test_append_only` |
| § 5 reader | FR-016, SC-012 | I-12 | `test_user_consent.py::test_latest_consent` |
