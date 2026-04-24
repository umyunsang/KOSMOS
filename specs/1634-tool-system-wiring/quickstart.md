# Quickstart — Adding a new adapter after P3

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data Model**: [data-model.md](./data-model.md)

> Audience: contributor adding a new Korean public-service API adapter to KOSMOS *after* Epic #1634 (P3) ships. This walkthrough is the SC-006 measurement target — a fresh contributor must reach a working adapter without editing any central registry, TUI tool wrapper, or routing module.

## 1. Prerequisites

- KOSMOS checked out, `uv sync` complete, `uv run pytest` passes from a clean main.
- Decision made: which Korean ministry/agency owns the API. Map to the `Ministry` enum in `src/kosmos/tools/models.py`. If the institution is not in the enum, open a small PR to add it before continuing (do NOT use `OTHER` for new permanent adapters).
- Decision made: which primitive backs the adapter — `lookup` (read), `submit` (side-effecting), `verify` (credential delegation), `subscribe` (streaming).

## 2. Create the adapter file

```bash
mkdir -p src/kosmos/tools/<ministry_lower>/
touch src/kosmos/tools/<ministry_lower>/<verb>_<resource>.py
```

Skeleton:

```python
"""<Ministry> <resource> <verb> adapter.

Citizen scenario: <one-line plain-Korean description>.
Reference: <upstream API spec URL or restored-src path>.
"""

from pydantic import BaseModel, Field

from kosmos.tools.models import GovAPITool


class <Verb><Resource>Input(BaseModel):
    # Pydantic v2 — no Any per Constitution § III
    region: str = Field(description="시도/시군구 코드 — see <enum reference>")
    date: str = Field(description="ISO-8601 date, default today")


class <Verb><Resource>Output(BaseModel):
    items: list[<NestedItem>]
    fetched_at: str  # ISO-8601 timestamp


TOOL = GovAPITool(
    id="<ministry_lower>_<resource>_<verb>",
    name_ko="<한국어 표시 이름>",
    ministry="<MINISTRY_ENUM>",       # Required; Literal alias
    category=["<topic>", "<topic>"],   # Non-empty list of Korean topic tags
    endpoint="https://<api host>",
    auth_type="public",                # or "api_key" / "oauth"
    input_schema=<Verb><Resource>Input,
    output_schema=<Verb><Resource>Output,
    search_hint="<bilingual keywords>",  # e.g., "병원 hospital 진료 medical"
    auth_level="public",               # AALLevel; per Spec 025 v6 must match TOOL_MIN_AAL row
    pipa_class="non_personal",         # or "personal_standard" / "_sensitive" / "_unique_id"
    is_irreversible=False,             # True only if action cannot be undone
    dpa_reference=None,                # Required when pipa_class != "non_personal"
    primitive="lookup",                # One of {lookup, submit, verify, subscribe, resolve_location}
    adapter_mode="live",               # or "mock"
    requires_auth=False,               # Fail-closed default is True; relax explicitly
    is_concurrency_safe=True,
    is_personal_data=False,
    cache_ttl_seconds=300,
    rate_limit_per_minute=60,
)


async def call(input: <Verb><Resource>Input) -> <Verb><Resource>Output:
    """Execute the adapter against the upstream API."""
    # ... httpx call here, unchanged from existing patterns
    raise NotImplementedError
```

## 3. Register the adapter

Append one line to `src/kosmos/tools/register_all.py`:

```python
from kosmos.tools.<ministry_lower>.<verb>_<resource> import TOOL as <verb_resource>_tool
# ... in the list-building function:
tools.append(<verb_resource>_tool)
```

That is the **only** central-registry edit. No TUI changes. No primitive wrapper changes. No routing-index changes.

## 4. Verify locally

```bash
# Unit test for the adapter (happy + error path required per Constitution § IV)
uv run pytest src/kosmos/tools/<ministry_lower>/test_<verb>_<resource>.py -v

# Routing consistency CI gate — must pass
uv run pytest tests/tools/test_routing_consistency.py -v

# Full backend test suite
uv run pytest
```

If `test_routing_consistency.py` fails, the message will name your adapter and the invariant violated — fix the offending field and re-run. See [contracts/routing-consistency.md](./contracts/routing-consistency.md) for the full invariant list.

## 5. Verify the LLM sees it

```bash
# Boot KOSMOS in TUI mode
bun run tui

# In the REPL, ask:
> 새로 추가한 어댑터 검색해줘 — 키워드 "<your search_hint>"
```

The LLM should issue a `lookup(mode="search", query="…")` call, receive your adapter in the top-K results (with `tool_id`, `primitive`, `ministry`, `score`, `search_hint`), and then optionally call `lookup(mode="fetch", tool_id="<your tool_id>", params={…})` to invoke it.

If your adapter does NOT appear in the search results: BM25 indexing happens at registration time — confirm `register_all.py` was modified and KOSMOS was restarted.

## 6. What NOT to edit

The following files are central infrastructure and should NOT be touched when adding a routine new adapter:

| File | Reason |
|---|---|
| `src/kosmos/tools/models.py` | GovAPITool schema. Edit only when adding a ministry to the enum (small dedicated PR). |
| `src/kosmos/tools/registry.py` | Registry mechanics. Edit only via spec-driven epic. |
| `src/kosmos/tools/routing_index.py` | Routing validation. Edit only via spec-driven epic. |
| `src/kosmos/tools/permissions.py` | Permission tier helper. Edit only via spec-driven epic. |
| `src/kosmos/ipc/mcp_server.py` | MCP server stub. Edit only via spec-driven epic. |
| `tui/src/tools/primitive/*.ts` | Primitive wrappers. Edit only via spec-driven epic. |
| `tui/src/ipc/mcp.ts` | MCP client. Edit only via spec-driven epic. |
| Anything under `src/kosmos/primitives/*.py` | Spec 031 primitive logic. Edit only via spec-driven epic. |

If you find yourself wanting to edit one of these to support your new adapter, **stop and open an issue** — the adapter contract may be insufficient and the central infrastructure may need a spec amendment.

## 7. Plugin path (P5 future)

After P5 (Epic #1636) ships, contributors who are NOT KOSMOS maintainers add adapters via the plugin system using the `plugin.<id>.<verb>` namespace. The internal walkthrough above remains valid for KOSMOS-internal adapters; the plugin walkthrough will live in `docs/plugins/quickstart.md` after P5.

## 8. Mock adapter walkthrough

For mock adapters (recorded fixture or shape-compatible synthetic), the path is the same with three differences:

1. File lives under `src/kosmos/tools/mock/<verb>_<resource>.py`.
2. `adapter_mode="mock"` MUST be declared explicitly (CI invariant 3).
3. The `AdapterRegistration.source_mode` field on the related Spec 031 record indicates mirror fidelity: `OPENAPI` (byte-mirrored from a public spec), `OOS` (shape-mirrored from open-source SDK), `HARNESS_ONLY` (net-new with no external mirror — per `feedback_mock_evidence_based`).

Mock adapters return their fixtures synchronously without network I/O; the function body looks like:

```python
async def call(input: <Verb><Resource>Input) -> <Verb><Resource>Output:
    return <Verb><Resource>Output.model_validate({
        "items": [...],
        "fetched_at": "2026-04-24T00:00:00+09:00",
    })
```

## 9. Time budget

A contributor adding a routine new adapter should reach a working `lookup(mode="fetch")` end-to-end in **under 2 hours** including the unit test. If the budget is exceeded by 2× and you are not blocked on upstream API documentation, the central infrastructure may have a usability gap — open an issue with the friction point.
