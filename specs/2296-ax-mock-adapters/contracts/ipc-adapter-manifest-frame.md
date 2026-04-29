# Contract — `AdapterManifestSyncFrame` IPC Frame

**Spec**: [../spec.md](../spec.md) FR-015 / FR-016 / FR-017 / FR-018 / FR-019 / FR-020
**Data model**: [../data-model.md § 4 + § 5](../data-model.md)
**Backward compatibility**: This contract adds the **21st arm** to the existing 20-arm `IPCFrame` discriminated union (Spec 032). Existing 20 arms unchanged.

---

## 1. Frame shape (JSON wire form)

```json
{
  "version": "1.0",
  "kind": "adapter_manifest_sync",
  "role": "backend",
  "correlation_id": "01HXKQ7Z3M1V8K2YQ8A6P4F9C1",
  "timestamp": "2026-04-29T10:15:23.456Z",
  "trailer": null,
  "entries": [
    {
      "tool_id": "resolve_location",
      "name": "Resolve Location",
      "primitive": "resolve_location",
      "policy_authority_url": null,
      "source_mode": "internal"
    },
    {
      "tool_id": "lookup",
      "name": "Lookup",
      "primitive": "lookup",
      "policy_authority_url": null,
      "source_mode": "internal"
    },
    {
      "tool_id": "nmc_emergency_search",
      "name": "NMC Emergency Bed Availability",
      "primitive": "lookup",
      "policy_authority_url": "https://www.e-gen.or.kr/nemc/main.do",
      "source_mode": "live"
    },
    {
      "tool_id": "mock_submit_module_hometax_taxreturn",
      "name": "Mock — Hometax Comprehensive Income Tax Return Submission",
      "primitive": "submit",
      "policy_authority_url": "https://www.hometax.go.kr/.../api-policy.do",
      "source_mode": "mock"
    }
  ],
  "manifest_hash": "8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b",
  "emitter_pid": 47823
}
```

## 2. Field semantics

| Field | Type | Required | Description |
|---|---|---|---|
| `version` | `"1.0"` | ✅ | Spec 032 envelope version, unchanged |
| `kind` | `"adapter_manifest_sync"` | ✅ | The new 21st discriminator value |
| `role` | `"backend"` | ✅ | Always backend-emitted |
| `correlation_id` | UUIDv7 string | ✅ | Per Spec 032 envelope |
| `timestamp` | ISO 8601 UTC | ✅ | Frame mint time |
| `trailer` | object \| null | ❌ | Per Spec 032; typically null for boot-time emission |
| `entries` | array of `AdapterManifestEntry` | ✅ | Non-empty, no duplicate `tool_id` |
| `manifest_hash` | 64-char lowercase hex | ✅ | SHA-256 of canonical-JSON-serialised `entries` (sorted by `tool_id`) |
| `emitter_pid` | positive int | ✅ | Backend process PID at boot |

## 3. Invariants (enforced at frame construction by Pydantic v2 validators)

- **I1** `entries` is non-empty
- **I2** No two entries share the same `tool_id`
- **I3** `manifest_hash == sha256(canonical_json(sorted(entries, key=lambda e: e.tool_id)))`. Caller MUST compute and supply; receiver MUST verify
- **I4** Every entry with `source_mode in ("live", "mock")` has a non-null HTTPS `policy_authority_url`
- **I5** Entries with `source_mode == "internal"` (only `resolve_location` and `lookup`) MUST have `policy_authority_url == null`
- **I6** `entries[*].primitive` matches the `AdapterPrimitive` enum exactly (no string aliases)
- **I7** `entries[*].tool_id` matches `^[a-z][a-z0-9_]*$` (lowercase snake-case)

Validator failures at construction time fail closed with `ValueError`; the backend boot fails with `SystemExit(78)` per Constitution § II + Spec 1634 boot-validation pattern.

## 4. Discriminated union impact

Before Epic ε:

```python
IPCFrame = Annotated[
    UserInputFrame
    | ChatRequestFrame
    | ... (18 more arms) ...
    | PluginOpFrame,
    Field(discriminator="kind"),
]
```

After Epic ε:

```python
IPCFrame = Annotated[
    UserInputFrame
    | ChatRequestFrame
    | ... (18 more arms) ...
    | PluginOpFrame
    | AdapterManifestSyncFrame,   # NEW — 21st arm
    Field(discriminator="kind"),
]
```

The discriminator field (`kind`) now accepts 21 distinct literal values. Spec 032's ring-buffer replay invariant (one schema shape per `kind` value) preserved.

## 5. Lifecycle

### 5.1 Backend emission (Python)

The backend emits exactly one `AdapterManifestSyncFrame` after `register_all_tools()` completes successfully and `build_routing_index()` validates. The frame is the **first non-handshake frame** the TUI receives. Implementation in `src/kosmos/ipc/adapter_manifest_emitter.py`:

```python
async def emit_manifest(stdout_writer, registry, sub_registries, *, pid: int) -> None:
    entries = sorted(
        [
            AdapterManifestEntry(
                tool_id=t.tool_id,
                name=t.name_or_default(),
                primitive=t.primitive,
                policy_authority_url=t.real_domain_policy.policy_authority_url if t.source_mode != "internal" else None,
                source_mode=t.source_mode,
            )
            for t in registry.iter_all() + [adapter for sub in sub_registries for adapter in sub.iter_all()]
        ],
        key=lambda e: e.tool_id,
    )
    manifest_hash = sha256(canonical_json(entries).encode()).hexdigest()
    frame = AdapterManifestSyncFrame(
        role="backend",
        correlation_id=str(uuid7()),
        timestamp=datetime.now(UTC),
        entries=entries,
        manifest_hash=manifest_hash,
        emitter_pid=pid,
    )
    await stdout_writer.write(frame.model_dump_json().encode() + b"\n")
    await stdout_writer.drain()
```

### 5.2 TUI consumption (TypeScript)

The TS-side `tui/src/services/api/adapterManifest.ts` exposes a singleton in-memory cache:

```typescript
let cache: AdapterManifestCache | null = null;

export function ingestManifestFrame(frame: AdapterManifestSyncFrame): void {
  // Replace, do NOT merge (FR-016).
  cache = {
    entries: new Map(frame.entries.map(e => [e.tool_id, e])),
    manifestHash: frame.manifest_hash,
    emitterPid: frame.emitter_pid,
    ingestedAt: new Date(),
  };
}

export function resolveAdapter(tool_id: string): AdapterManifestEntry | undefined {
  return cache?.entries.get(tool_id);
}

export function isManifestSynced(): boolean {
  return cache !== null;
}
```

The IPC frame router (existing TUI code that consumes the JSONL stream) gets a new branch on `kind === 'adapter_manifest_sync'` calling `ingestManifestFrame`.

### 5.3 Primitive validateInput integration (TypeScript)

Each of the four primitives (`LookupPrimitive`, `SubmitPrimitive`, `VerifyPrimitive`, `SubscribePrimitive`) modifies its `validateInput` body (current single-tier `context.options.tools.find(...)`) to a two-tier resolution:

```typescript
async validateInput(input, context) {
  // Tier 0 — fail closed if manifest not yet synced (FR-019).
  if (!isManifestSynced()) {
    return { result: 'error', message: 'Adapter manifest not yet synced from backend; retry once boot completes.' };
  }

  // Tier 1 — synced backend manifest (FR-017).
  const backendEntry = resolveAdapter(input.tool_id);
  if (backendEntry) {
    const citation = backendEntry.policy_authority_url
      ? { url: backendEntry.policy_authority_url, source: 'agency-published' }
      : null;
    setKosmosCitations(context, citation);
    return { result: 'allow' };
  }

  // Tier 2 — TS-side internal tools fallback (existing path).
  const internalTool = context.options.tools.find(t => t.name === input.tool_id);
  if (internalTool) {
    const citation = extractCitation(internalTool);
    setKosmosCitations(context, citation);
    return { result: 'allow' };
  }

  // Fail closed (FR-020).
  return { result: 'error', message: `AdapterNotFound: '${input.tool_id}' is not in the synced backend manifest or the internal tools list.` };
}
```

## 6. Failure modes

| Mode | Trigger | Behaviour |
|---|---|---|
| **Cold-boot race** | TUI calls `validateInput` before any manifest frame arrives | Tier 0 returns error with `"manifest not yet synced"`. LLM is expected to retry once. |
| **Adapter not found** | `tool_id` absent from both synced manifest and internal-tools list | Tier 2 returns error with `"AdapterNotFound: '<id>'"`. LLM is expected to call `lookup(mode='search', ...)` to discover. |
| **Duplicate `tool_id` in frame** | Backend emitter bug | Pydantic validator I2 rejects at construction; backend exits with `SystemExit(78)` before frame is sent. |
| **Manifest hash mismatch** | Wire-corruption or emitter bug | TS-side recomputes the hash on receive; mismatch logs an error but ingests anyway (manifest content is the source of truth, hash is a check). |
| **Internal entry has policy URL** | Spec violation by future contributor | Pydantic validator I5 rejects at construction. |

## 7. Test surface

Mandatory tests gated by this contract:

1. **Round-trip serialisation** (Python pytest): construct `AdapterManifestSyncFrame`, dump JSON, parse with `IPCFrame` discriminated union, assert all fields match.
2. **Discriminator validation** (Python pytest): assert `IPCFrame.model_validate({"kind": "adapter_manifest_sync", ...})` returns an `AdapterManifestSyncFrame` instance.
3. **Hash mismatch handling** (Python pytest): construct entries, mutate one, assert SHA-256 detects.
4. **Cache replace, not merge** (TypeScript bun test): ingest two frames, assert second wholly replaces first.
5. **Cold-boot race** (TypeScript bun test): invoke `validateInput` before any frame, assert `error: 'manifest not yet synced'`.
6. **Tier-1 resolves backend adapter** (TypeScript bun test): ingest frame with `nmc_emergency_search`, invoke `lookupPrimitive.validateInput({tool_id: 'nmc_emergency_search', ...})`, assert success + citation populated.
7. **Tier-2 fallback** (TypeScript bun test): ingest frame without `WebFetch`, invoke `lookupPrimitive.validateInput({tool_id: 'WebFetch', ...})`, assert success via internal-tools path.
8. **AdapterNotFound** (TypeScript bun test): no entry for `bogus_tool_id`, assert error mentions the unknown ID.
9. **21-arm union exhaustive** (Python pytest): import `IPCFrame`, assert it has exactly 21 arms (regression guard against Epic ε accidentally re-extending an existing arm).

All nine tests gate the FR-015–FR-020 acceptance.
