# Contract: Live Test Fixtures

**Feature**: [spec.md](../spec.md) · **Plan**: [plan.md](../plan.md)

This contract specifies the public surface of the two new pytest fixtures added to `tests/live/conftest.py`. Test modules depend only on the contract below, not on implementation details.

---

## Fixture: `kakao_api_key`

### Signature

```python
@pytest.fixture(scope="session")
def kakao_api_key() -> str: ...
```

### Contract

| Aspect | Guarantee |
|---|---|
| **Return type** | `str` — the Kakao REST API key, non-empty after `.strip()`. |
| **Scope** | `session` — resolved once per test session, cached across tests. |
| **Source** | `os.environ["KOSMOS_KAKAO_API_KEY"]`. |
| **Missing env var behavior** | `pytest.fail("set KOSMOS_KAKAO_API_KEY to run live geocoding tests")`. **Exact string** — no formatting, no trailing period. |
| **Whitespace policy** | Empty-string (including whitespace-only) is treated as missing. |
| **No fallback** | Never `pytest.skip`, never `xfail`. |

### Consumers

- `tests/live/test_live_geocoding.py` — every test.
- `tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address`.

### Spec traceability

FR-004 · FR-008 · FR-011 · Story 1 AS-8 · SC-004

---

## Fixture: `kakao_rate_limit_delay`

### Signature

```python
@pytest_asyncio.fixture
async def kakao_rate_limit_delay() -> Callable[[], Awaitable[None]]: ...
```

### Contract

| Aspect | Guarantee |
|---|---|
| **Yields** | An awaitable callable (or async context manager) that sleeps a fixed delay when invoked. |
| **Default delay** | 200 ms. Adjustable via a private module-level constant (not exposed as fixture parameter). |
| **Scope** | `function` — no cross-test state retained. **Not autouse.** |
| **Placement** | Called explicitly by geocoding tests between successive Kakao API calls within a single test function. |
| **Composition** | Compatible with the existing autouse `_live_rate_limit_pause` (post-test 10 s cooldown) — they do not overlap or double-apply. |

### Consumers

- `tests/live/test_live_geocoding.py` — any test that makes ≥2 Kakao calls in sequence.

### Spec traceability

FR-005 · FR-014 · SC-006

---

## Existing fixtures (inherited from #291, no change)

| Fixture | Purpose |
|---|---|
| `friendli_token` | Session-scoped FriendliAI token. |
| `data_go_kr_api_key` | Session-scoped data.go.kr key. |
| `koroad_api_key` | Alias of `data_go_kr_api_key` for KOROAD tests. |
| `live_http_client` | Plain `httpx.AsyncClient` with 30 s timeout. |
| `friendli_http_client` | Pre-configured `httpx.AsyncClient` for FriendliAI. |
| `_live_rate_limit_pause` | Autouse 10 s post-test cooldown (FriendliAI rate-limit). |

These fixtures MUST remain unmodified. The new Kakao fixtures add to the surface without renaming or altering existing behavior.
