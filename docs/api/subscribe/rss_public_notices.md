---
tool_id: mock_rss_public_notices_v1
primitive: subscribe
tier: mock
permission_tier: 1
---

# mock_rss_public_notices_v1

## Overview

Subscribes to Korean government public notice RSS feeds and streams `RssItemEvent` fixtures drawn from a simulated data.go.kr RSS 2.0 feed, with per-subscription `guid` de-duplication via `RssGuidTracker`.

| Field | Value |
|---|---|
| Classification | Mock · Permission tier 1 |
| Source | data.go.kr RSS feeds + Korea.kr 정책뉴스 RSS (https://www.korea.kr/rss/), conforming to the RSS 2.0 standard (https://www.rssboard.org/rss-specification) |
| Primitive | `subscribe` |
| Module | `src/kosmos/tools/mock/data_go_kr/rss_notices.py` |

## Envelope

**Input model**: `SubscribeInput` (from `kosmos.primitives.subscribe`) with the following adapter-specific `params` keys.

| Field | Type | Required | Description |
|---|---|---|---|
| `tool_id` | `str` | yes | Must be `"mock_rss_public_notices_v1"` |
| `params.item_delay_seconds` | `float` | no | Delay between yielded items (default `0.05`) |
| `params.reset_guids` | `bool` | no | If `true`, the `RssGuidTracker` resets after the first pass, simulating a publisher that reuses guids (default `false`) |
| `params.repeat_count` | `int` | no | Number of full passes over the fixture set (default `1`) |

**Output model**: `RssItemEvent` (from `kosmos.primitives.subscribe`) — one event per unique guid item.

| Field | Type | Required | Description |
|---|---|---|---|
| `feed_tool_id` | `str` | yes | Echo of `inp.tool_id` — identifies which feed produced the item |
| `guid` | `str` | yes | RSS 2.0 guid; de-duplicated per `RssGuidTracker` within this handle |
| `published_at` | `datetime` | yes | Parsed from RFC 3339 `pubDate` field |
| `title` | `str` | yes | Notice title (e.g. `국토교통부 공고 제2026-001호 — 도시개발구역 지정`) |
| `link` | `str | None` | no | URL to full notice body |
| `description` | `str | None` | no | Brief notice summary |

## Search hints

- 한국어: `공고`, `정부공지`, `행정공고`, `정책뉴스`, `RSS`
- English: `public notice`, `government announcement`, `RSS feed`, `ministry bulletin`

## Endpoint

- **Mode**: Fixture-replay only
- **Public spec source**: RSS 2.0 specification (https://www.rssboard.org/rss-specification) — the adapter shape mirrors the standard RSS 2.0 `<item>` element (`guid`, `title`, `link`, `pubDate`, `description`). Ministry feed endpoints follow the same schema (e.g., Korea.kr 정책뉴스 RSS: https://www.korea.kr/rss/, data.go.kr 공지사항 RSS: https://www.data.go.kr/rss/).
- **Fixture path**: `tests/fixtures/data_go_kr/rss_notices/` (4 static items simulating notices from MOLIT, MOHW, MOIS, and MOE)

## Permission tier rationale

This adapter sits at permission tier 1 (green ⓵) because government public notices are open, non-personal data published without authentication requirements. Spec 033 defines tier 1 for read-only streams that carry no PII and impose no citizen consent obligation. RSS feeds from data.go.kr and Korea.kr are publicly available without API keys; the `mock_rss_public_notices_v1` adapter mirrors this tier by requiring no auth (`requires_auth=False` implicit at tier 1). The per-subscription `RssGuidTracker` is a harness-internal de-dup mechanism with no impact on the permission model.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "mock_rss_public_notices_v1",
  "params": {
    "item_delay_seconds": 0.05,
    "repeat_count": 1
  }
}
```

### Output envelope (success)

```json
{
  "events": [
    {
      "feed_tool_id": "mock_rss_public_notices_v1",
      "guid": "notice-2026-001",
      "published_at": "2026-04-19T09:00:00+09:00",
      "title": "국토교통부 공고 제2026-001호 — 도시개발구역 지정",
      "link": "https://www.data.go.kr/notices/2026-001",
      "description": "서울시 강남구 일원 도시개발구역 지정 공고입니다."
    },
    {
      "feed_tool_id": "mock_rss_public_notices_v1",
      "guid": "notice-2026-002",
      "published_at": "2026-04-19T10:00:00+09:00",
      "title": "보건복지부 공고 제2026-002호 — 의료기관 인증 기준 개정",
      "link": "https://www.data.go.kr/notices/2026-002",
      "description": "의료기관 인증 평가 기준 개정 사항 안내."
    }
  ]
}
```

### Conversation snippet

```text
Citizen: 최근 정부 공고를 알려주세요.
KOSMOS: 최근 공고 4건을 수신했습니다. 국토교통부는 강남구 일원에 도시개발구역을 지정하는 공고를, 보건복지부는 의료기관 인증 기준 개정 사항을 안내했습니다.
```

## Constraints

- **Rate limit**: N/A (fixture mode). Real RSS feeds from data.go.kr / Korea.kr are publicly available and are not subject to documented per-minute request caps, but aggressive polling is discouraged; the REST-pull adapter (`mock_rest_pull_tick_v1`) enforces a 10s floor for polled feeds.
- **Freshness window**: N/A — fixtures are static. Real RSS feeds are typically refreshed on a ministry-specific schedule (e.g., hourly or daily).
- **Fixture coverage gaps**: Only 4 items from 4 ministries are provided. Fixtures do not cover: paginated feeds with `<nextPage>` semantics, items with missing `link` or `description`, or publisher `guid` reuse scenarios (use `reset_guids=true` + `repeat_count=2` to exercise the de-dup edge case).
- **Error envelope examples**:
  - Tier-1 fail (handle expired): the async generator returns cleanly when `handle.closes_at` is exceeded; no error event is emitted.
  - Tier-2 / Tier-3 (auth) fail: N/A — RSS public notices adapter is tier 1, no authentication required.
  - Network timeout: N/A in fixture mode. In a live RSS integration, a `httpx.TimeoutException` from the upstream feed would be caught by the harness retry layer and surfaced as `{"kind": "error", "reason": "upstream_unavailable", "message": "RSS feed did not respond within 10s"}`.
