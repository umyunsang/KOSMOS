# Spec 031 — Five-Primitive Harness Contracts

**Branch**: `031-five-primitive-harness` | **Date**: 2026-04-19 | **Spec**: [../spec.md](../spec.md)

JSON Schema Draft 2020-12 exports of the Pydantic v2 I/O surface defined in [`../data-model.md`](../data-model.md). Each schema is the canonical contract for a primitive and MUST be kept in sync with its Pydantic source at implementation time.

## Primitive ↔ schema map

| Primitive | Input schema | Output schema | Status |
|---|---|---|---|
| `lookup` | [`../../022-mvp-main-tool/contracts/lookup.input.schema.json`](../../022-mvp-main-tool/contracts/lookup.input.schema.json) | [`../../022-mvp-main-tool/contracts/lookup.output.schema.json`](../../022-mvp-main-tool/contracts/lookup.output.schema.json) | **Preserved byte-identical** from Spec 022 per FR-016 |
| `resolve_location` | [`../../022-mvp-main-tool/contracts/resolve_location.input.schema.json`](../../022-mvp-main-tool/contracts/resolve_location.input.schema.json) | [`../../022-mvp-main-tool/contracts/resolve_location.output.schema.json`](../../022-mvp-main-tool/contracts/resolve_location.output.schema.json) | **Preserved byte-identical** from Spec 022 per FR-017 |
| `submit` | [`submit.input.schema.json`](./submit.input.schema.json) | [`submit.output.schema.json`](./submit.output.schema.json) | New |
| `subscribe` | [`subscribe.input.schema.json`](./subscribe.input.schema.json) | [`subscribe.output.schema.json`](./subscribe.output.schema.json) | New |
| `verify` | [`verify.input.schema.json`](./verify.input.schema.json) | [`verify.output.schema.json`](./verify.output.schema.json) | New |

## Registry contract

- [`adapter_registration.schema.json`](./adapter_registration.schema.json) — `AdapterRegistration` metadata including Spec 031 dual-axis (`published_tier_minimum`, `nist_aal_hint`) + Spec 024/025 `auth_type`/`auth_level`/`pipa_class`/V1–V6 invariants.

## Conventions

- All `additionalProperties: false` — closed object shapes per `ConfigDict(extra="forbid")`.
- All enums closed — adding a value is a spec amendment (Edge Case in spec §120–131).
- All timestamps are RFC 3339 with timezone (data-model §Convention); skew tolerance ±300s per Spec 024 I4.
- Discriminator keywords (`kind`, `family`, `mode`) match Pydantic v2 `Field(discriminator=...)`.
- `params: dict[str, object]` on main-surface envelopes — adapter owns the typed schema (see `AdapterRegistration.input_model_ref`).

## Cross-references

- [Spec 022 contracts (preserved)](../../022-mvp-main-tool/contracts/README.md)
- [Spec 024 ToolCallAuditRecord](../../024-tool-security-v1/contracts/tool_call_audit_record.schema.json)
- [Spec 025 V6 canonical auth-type↔auth-level mapping](../../025-tool-security-v6/contracts/)

## Banned strings (FR-002, SC-002)

The `submit.input.schema.json` and `submit.output.schema.json` MUST NOT contain any of the following legacy 8-verb field names anywhere in their property trees:

`check_eligibility`, `reserve_slot`, `subscribe_alert`, `pay`, `issue_certificate`, `submit_application`, `declared_income_krw`, `certificate_type`, `family_register`, `resident_register`

Enforced by `tests/test_submit_banned_words.py` (Phase 2 task).
