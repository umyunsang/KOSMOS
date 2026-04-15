# Contracts — MVP Main-Tool

JSON-Schema exports of the two LLM-facing tool contracts. These are the exact shapes the LLM sees via FriendliAI Serverless (OpenAI-compatible) tool-use introspection.

## Files

- `resolve_location.input.schema.json` — `ResolveLocationInput` model (see `data-model.md §1`)
- `resolve_location.output.schema.json` — `ResolveLocationOutput` discriminated union (`data-model.md §2`)
- `lookup.input.schema.json` — `LookupInput` discriminated on `mode` (`data-model.md §3`)
- `lookup.output.schema.json` — `LookupOutput` discriminated union (`data-model.md §4`)

## Generation

These JSON Schemas are produced by Pydantic v2's `.model_json_schema()` at build time. The hand-authored versions below are the authoritative contract for review; the runtime exports MUST match.

## Frozen invariants

- `kind` discriminator values are binding. No renames without an ADR.
- `reason` enum values for `LookupError` and `ResolveError` are binding.
- `mode` discriminator values (`"search"`, `"fetch"`) for `LookupInput` are binding.
- `source` enum values on `resolve_location` outputs are binding.
- Removing a field is a breaking change requiring a major-version bump of the tool schema and an ADR.
