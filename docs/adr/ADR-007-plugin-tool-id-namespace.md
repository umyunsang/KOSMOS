# ADR-007: Plugin Tool ID Namespace Extension

**Status**: Accepted
**Date**: 2026-04-25
**Epic**: #1636 (P5 Plugin DX 5-tier)
**Affected**: `src/kosmos/tools/registry.py:AdapterRegistration` · `src/kosmos/tools/models.py:LookupFetchInput` · `src/kosmos/tools/models.py:GovAPITool._validate_id` (extended in T014; the runtime registry holds GovAPITool instances, so the same alternation must apply there for plugin tools to round-trip through `ToolRegistry.register`)

## Context

Migration tree § L1-C C7 mandates that plugin-contributed tools live under the namespace `plugin.<plugin_id>.<verb>` where `<verb>` is one of the 4 root primitives (`lookup` / `submit` / `verify` / `subscribe`). This prevents adapter-id collisions across third-party plugins and makes the plugin origin visible in the LLM's `lookup` discovery surface.

The existing `AdapterRegistration.tool_id` and `LookupFetchInput.tool_id` fields enforce a snake-case pattern `^[a-z][a-z0-9_]*$` (Spec 022/031). Dots are rejected, so the canonical plugin-namespaced form would fail validation at registration and at `lookup(mode="fetch")` time.

Spec #1636 (Plugin DX 5-tier) requires `PluginManifest` to compose `AdapterRegistration` so the existing Spec 022/024/025/031 invariant chain (V1–V6) applies for free. Composition with a stricter regex than the manifest's contract surface is incompatible.

## Decision

Extend the `tool_id` regex on both `AdapterRegistration` (Spec 031 registry metadata) and `LookupFetchInput` (Spec 022 fetch surface) to accept either:

1. **Built-in form** — `^[a-z][a-z0-9_]*$` (existing Spec 022/031 adapters such as `koroad_accident_hazard_search`, `kma_short_term_forecast`).
2. **Plugin-namespaced form** — `^plugin\.[a-z][a-z0-9_]*\.(lookup|submit|verify|subscribe|resolve_location)$` (new for Spec 1636).

The combined pattern is a backward-compatible alternation:

```regex
^([a-z][a-z0-9_]*|plugin\.[a-z][a-z0-9_]*\.(lookup|submit|verify|subscribe|resolve_location))$
```

## Rationale

- **Migration tree alignment**: § L1-C C7 explicitly names `plugin.<plugin_id>.<verb>`. Anything else dilutes the canonical namespace decision.
- **Backward compatibility**: every existing snake_case `tool_id` continues to validate; no Spec 022/031 adapter needs editing.
- **Single enforcement point**: the regex is the only structural check; per-verb constraints (Q8-VERB-IN-PRIMITIVES, Q8-NO-ROOT-OVERRIDE) are layered on top by `PluginManifest` validators (Spec 1636 T006).
- **No new runtime dependencies** — `re` only.
- **Preserves Spec 025 V6 backstop**: the auth-level allow-list is unaffected; this change is only about identifier shape.

## Alternatives considered

- **Decoupled mapping** — keep the regex strict and have `PluginManifest` carry a separate `dotted_tool_id` field, mapping to a snake_case `internal_tool_id` for `AdapterRegistration`. *Rejected*: introduces a drift surface (two identifiers per plugin); the LLM-visible name would diverge from the registry key, complicating `lookup(mode="fetch")` traceability.
- **Presentation-only namespace** — keep dots only in display strings, store snake_case everywhere. *Rejected*: would weaken the migration tree intent (the namespace is meant to be load-bearing, not cosmetic).

## Consequences

- `AdapterRegistration` and `LookupFetchInput` accept the new dotted form starting on `feat/1636-plugin-dx-5tier`.
- `PluginManifest._v_namespace` validator (Spec 1636 T006) refines the constraint further: when `tool_id` matches the dotted form, it must additionally satisfy `tool_id == f"plugin.{plugin_id}.<verb>"` and `<verb> ∈ {lookup, submit, verify, subscribe}` (note: `resolve_location` is allowed by the registry regex for parity with the 5-primitive set, but plugin manifests today restrict to the 4 LLM-visible verbs).
- Spec 022/024/025/031 invariant chain is preserved — the regex is the only field that changed.
- No ToolRegistry test needs editing; new tests in `kosmos.plugins.tests` cover the plugin form.

## References

- `docs/requirements/kosmos-migration-tree.md § L1-C C7`
- `specs/1636-plugin-dx-5tier/spec.md § FR-022`
- `specs/1636-plugin-dx-5tier/data-model.md § 1`
- `specs/1636-plugin-dx-5tier/contracts/manifest.schema.json`
- Memory `feedback_main_verb_primitive`
