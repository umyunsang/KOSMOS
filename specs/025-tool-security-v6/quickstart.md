# V6 Quickstart — for Adapter Authors and Reviewers

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-04-17

## Who this is for

- Adapter authors adding a new `GovAPITool` after V6 lands.
- Security / governance reviewers auditing a PR that changes `auth_type` or `auth_level`.
- Auditors reading the tool registry and wondering which `(auth_type, auth_level)` combinations are legal.

## The V6 rule in one sentence

`GovAPITool.auth_type` and `GovAPITool.auth_level` MUST be a pair in this allow-list:

| `auth_type` | Allowed `auth_level` values |
|---|---|
| `public` | `public`, `AAL1` |
| `api_key` | `AAL1`, `AAL2`, `AAL3` |
| `oauth` | `AAL1`, `AAL2`, `AAL3` |

Everything else is rejected at `GovAPITool` construction time (layer 1) and again at `ToolRegistry.register()` time (layer 2, defense against pydantic bypass).

## What to do when adding a new adapter

1. **Pick your `auth_type`** based on the upstream API:
   - No credential needed → `"public"`.
   - API key / static token → `"api_key"`.
   - OAuth2 flow → `"oauth"`.
2. **Pick your `auth_level`** based on the assurance required for citizen data exposure:
   - No personal data, no session required → `"public"`. Requires `auth_type="public"` AND `requires_auth=False` (V5).
   - Authenticated session, minimal assurance → `"AAL1"`.
   - Multi-factor, sensitive data → `"AAL2"`.
   - Highest assurance, irreversible actions → `"AAL3"`.
3. **Check the allow-list table above.** If your pair is ❌, choose differently or justify (via ADR) extending the mapping in `src/kosmos/tools/models.py`.
4. **Construct the `GovAPITool`**. If V6 rejects, the error names both fields and the allowed set — follow the message.
5. **Register the tool**. The registry backstop re-checks V6; this catches cases where you built the instance via `model_construct` or mutated a field after construction (don't do that).

## The approved MVP-meta-tool pattern (not an exception)

`resolve_location` and `lookup` use:

```python
auth_type="public"
auth_level="AAL1"
requires_auth=True
```

This is a **compliant V6 configuration**, not a carve-out:
- V6 allows `(public, AAL1)` per the canonical mapping.
- V5 allows `requires_auth=True` because `auth_level != "public"`.
- The orchestrator calls these tools directly (not through `PermissionPipeline.dispatch()`), and they require an authenticated citizen session for rate-limit accounting and audit continuity even though the upstream endpoint (or geocoder) needs no credential.

Any new meta-tool following this pattern is also allowed without special treatment.

## Why V6 exists (the threat it closes)

V5 alone enforces `auth_level=="public"` ⇔ `requires_auth==False`. But the legacy `PermissionPipeline.dispatch()` path derives access tier from `auth_type` (not `requires_auth`). Without V6, a future adapter with `auth_type="public" + auth_level="AAL2" + requires_auth=True` would:
- Pass V1–V5 cleanly.
- Be correctly auth-gated by `executor.invoke()` (which reads `requires_auth`).
- **Be anonymously callable through `dispatch()`** (which reads `auth_type="public"` as the access tier and decides "no auth needed").

V6 makes this misconfiguration impossible at the model layer, regardless of which runtime path dispatches the tool.

## Running the V6 tests locally

```bash
uv run pytest tests/tools/test_gov_api_tool_extensions.py -k V6 -v
uv run pytest tests/tools/test_registry_invariant.py -v
```

The second command includes the registry-wide scan test that asserts every production adapter passes V6. If this test fails, a recently added adapter has drifted outside the allow-list; fix the adapter, not the test.

## What you do NOT need to do

- ❌ You do not need to change `PermissionPipeline.dispatch()`. Its refactor is deferred to a separate Epic (see `spec.md § Deferred Items`).
- ❌ You do not need to alter `executor.invoke()`. It is already correct.
- ❌ You do not need to write new pytest fixtures for V6; existing `GovAPITool` fixtures cover construction.
- ❌ You do not need to update V1–V5 tests; V6 is purely additive.

## Where to read more

- [spec.md](./spec.md) — full feature spec (user stories, FR-039–FR-048, success criteria).
- [data-model.md](./data-model.md) — canonical mapping, validator-chain ordering, baseline snapshot of all existing adapters.
- [contracts/v6-error-contract.md](./contracts/v6-error-contract.md) — exact error message shapes (layer 1 and layer 2).
- `docs/security/tool-template-security-spec-v1.md` v1.1 (after implementation) — governance-artifact version of the mapping + worked examples.
