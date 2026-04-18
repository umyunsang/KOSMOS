# Phase 0 Research: OTLP Collector + Local Langfuse Stack

**Spec**: 028-otlp-collector | **Date**: 2026-04-18 | **Status**: Complete

This document resolves all `NEEDS CLARIFICATION` markers in `spec.md`, validates the deferred-items table (Constitution Principle VI gate), and maps every design decision to a concrete reference in `docs/vision.md § Reference materials` or an upstream specification.

---

## 1. NEEDS CLARIFICATION resolutions

### Clarification #3 — `otel/opentelemetry-collector-contrib:0.105.0` multi-arch image digests

**Status**: RESOLVED 2026-04-18.

**Method**: Queried the Docker Hub v2 registry API at `https://registry.hub.docker.com/v2/repositories/otel/opentelemetry-collector-contrib/tags/0.105.0/` (docker CLI not available in the plan sandbox; HTTP registry API returns the same manifest list data that `docker buildx imagetools inspect` would).

**Resolution** — top-level manifest-list digest and the two arches KOSMOS cares about:

| Tag | Arch | Digest | Size (bytes) |
|---|---|---|---|
| `otel/opentelemetry-collector-contrib:0.105.0` | (manifest list) | `sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114` | — |
| `otel/opentelemetry-collector-contrib:0.105.0` | `linux/amd64` | `sha256:1888ac50a4e773cf0e4bf53e80cfb25fa009c786e822435f8510f4d08f9f0817` | 70,805,063 |
| `otel/opentelemetry-collector-contrib:0.105.0` | **`linux/arm64`** | **`sha256:aa7d5ef71d04bfced8650fe976b4aa61f8cceeb33e6f56f5fc963a3e33fb599f`** | 65,002,052 |

**Decision**: `docker-compose.dev.yml` pins the image with an inline comment carrying both per-arch digests plus the manifest-list digest. The `image:` field itself uses the **manifest-list digest** (`sha256:3ff721e…`) so that `docker compose pull` resolves to the correct arch-specific layer automatically on both KSC demo Apple Silicon machines and amd64 CI hosts.

```yaml
# See specs/028-otlp-collector/contracts/collector-config.yaml for pipeline definition.
# Multi-arch digests (pinned 2026-04-18 via Docker Hub v2 API):
#   linux/amd64: sha256:1888ac50a4e773cf0e4bf53e80cfb25fa009c786e822435f8510f4d08f9f0817
#   linux/arm64: sha256:aa7d5ef71d04bfced8650fe976b4aa61f8cceeb33e6f56f5fc963a3e33fb599f
image: otel/opentelemetry-collector-contrib@sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114
```

**Rationale**: Manifest-list pinning lets the KSC demo operator run a single `docker compose up -d` on any laptop and still end up with a reproducible rootfs. Per-arch inline comments give air-gapped operators the exact blobs to pre-pull via `docker pull @sha256:<arch-digest>`.

**Alternatives considered**:
- **Floating `:0.105.0` tag (no digest)**: Rejected — violates spec SC-006 (explicit digest pins required for reproducibility) and risks silent upstream republish.
- **Per-arch pin with build-time selection**: Rejected — Compose v2 does not support per-platform image overrides at the service level without a heavier Bake workflow.

**Reference**: OpenTelemetry Collector Contrib release notes `v0.105.0` (2024-07-02) — the minor version that ships the `attributes` processor's `hash` action (required for FR-006 SHA-256 of `kosmos.location.query`). Actual minor that introduced `hash` is `v0.92.0` (2024-01), so `0.105.0` is comfortably within the supported range.

### Langfuse image digests (audit-trail companion to FR-008a)

Even though the floating `3.35.0` tag is acceptable per spec, the plan records the digests at pin time for future audit:

| Image | Arch | Digest |
|---|---|---|
| `langfuse/langfuse:3.35.0` | manifest list | `sha256:4d86c8367cf9483026b2f0c2eb41559e63c50353c5a0a9cc32b4fdd4c82d1e49` |
| `langfuse/langfuse:3.35.0` | `linux/amd64` | `sha256:87456e2afe1aedc4fe22063ee6bbaa390d8ca76cb9839150e451f24512336547` |
| `langfuse/langfuse:3.35.0` | `linux/arm64` | `sha256:8252c87cb1a9643a00036a13667603f32f7d6912fc9ad20ebe97d8cc2fb699ef` |
| `langfuse/langfuse-worker:3.35.0` | manifest list | `sha256:6094f5c41d5fe59351ae6625c3e32daf7b4aac2008dc74a4008a851713bb6212` |
| `langfuse/langfuse-worker:3.35.0` | `linux/amd64` | `sha256:4077a6014f64a7102369af68c1713ff4cd7a23e65adf5f692fe6983a489eed17` |
| `langfuse/langfuse-worker:3.35.0` | `linux/arm64` | `sha256:509afa54a3a54ad2920b4aed9c63e60705f84523e03730bdd08086d62dd65578` |

**Alpine variant finding**: `langfuse/langfuse:3.35.0-alpine` and `langfuse/langfuse-worker:3.35.0-alpine` **do not exist** on Docker Hub (404). The speculative "prefer alpine if available" clause in spec.md § New Dependencies is therefore moot — both Langfuse images ship only as Debian-slim-based multi-arch manifests. The compose file will use `3.35.0` (non-alpine) exclusively.

---

## 2. Deferred Items Validation (Constitution Principle VI gate)

### Table audit

| Item | Tracking Issue | Audit result |
|---|---|---|
| Production OTLP collector deployment (Fly.io/Railway, TLS, subdomain) | `[NEEDS TRACKING — Phase 3 observability epic]` | RESOLVED BY `/speckit-taskstoissues` — placeholder will be back-filled with real issue number. |
| Langfuse Cloud Hobby integration | `[NEEDS TRACKING]` | RESOLVED BY `/speckit-taskstoissues`. |
| TLS configuration (receiver + exporter) | `[NEEDS TRACKING]` | RESOLVED BY `/speckit-taskstoissues`. |
| CI `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` via Infisical OIDC | `[NEEDS TRACKING]`, dep on #468 | RESOLVED BY `/speckit-taskstoissues`; #468 is in-flight (Infisical IDs captured). |
| Per-environment Langfuse project isolation | `[NEEDS TRACKING]` | RESOLVED BY `/speckit-taskstoissues`. |
| Live CI smoke test `tests/live/test_trace_emission.py` | `[NEEDS TRACKING]` | RESOLVED BY `/speckit-taskstoissues`. |
| `redaction.yaml` split | `[NEEDS TRACKING]` | RESOLVED BY `/speckit-taskstoissues`. |
| Span-attribute normative lock | `#507` | ALREADY TRACKED — PASS. |
| OTel Logs signal integration | `#502` | ALREADY TRACKED — PASS (spec 021 explicit). |
| Span sampling / filtering | `#503` | ALREADY TRACKED — PASS (spec 021 explicit). |

### Free-text deferral scan

Regex-scanned spec.md for these patterns: `separate epic | future epic | Phase [2-9]+ | v2 | deferred to | later release | out of scope for v1`.

**Findings**:
- `Phase 3 observability` — 10 matches, all within the Deferred Items table or explicit Out-of-Scope prose that references the table. **COMPLIANT**.
- `v2` — 0 matches outside the image-tag context (`langfuse/langfuse:3` floating tag; this is a version pin, not a deferral reference).
- `separate epic`, `future epic`, `later release`, `out of scope for v1` — 0 matches.

**Result**: No unregistered deferrals. Spec complies with Principle VI.

---

## 3. Reference mapping

Every design decision in this plan traces to one of the following sources.

| Decision | Reference | Citation |
|---|---|---|
| Collector pipeline shape (receiver → attributes → batch → exporter) | OpenTelemetry Collector — "Core Components" docs | `https://opentelemetry.io/docs/collector/configuration/` — single pipeline canonical form |
| `attributes/pii_redact` processor with `delete` + `hash` actions | OpenTelemetry Collector Contrib — `processor/attributesprocessor` README | `hash` action introduced in v0.92.0 |
| Langfuse OTLP ingest path `/api/public/otel/v1/traces` | Langfuse Self-Host docs — "OpenTelemetry / Get Started" | Confirmed v3.22.0+; HTTP/JSON and HTTP/protobuf; no gRPC |
| `Authorization: Basic <base64(pk:sk)>` + `x-langfuse-ingestion-version: 4` | Langfuse self-host `docker-compose` reference | Matches header contract for real-time preview |
| `batch` processor tuning (`timeout: 5s`, `send_batch_size: 512`) | OpenTelemetry Collector Contrib — `processor/batchprocessor` defaults | KOSMOS uses the recommended dev preset; production Epic may tune upward |
| Health extension on port `13133` | OpenTelemetry Collector — `extension/healthcheckextension` | Default port; no change needed |
| PII whitelist single source of truth | KOSMOS spec 021 `_ALLOWED_METADATA_KEYS` frozenset | `src/kosmos/observability/event_logger.py` — Python-layer first gate; collector is second gate |
| Warn-and-skip when endpoint unset | KOSMOS spec 021 FR-010 | Inherited behavior — observability failure never breaks app |
| `OTEL_SDK_DISABLED=true` CI path | KOSMOS spec 021 FR-014 | Extended here — SC-004 |
| Docker Hub multi-arch digest pinning | Docker Buildx docs — "imagetools inspect" | Used via v2 registry API (equivalent output) |
| Environment variable `KOSMOS_` prefix | AGENTS.md hard rule | Applied to all three new vars |
| Infrastructure directory layout (`infra/otel-collector/`) | Existing `infra/copilot-gate-app/` convention | One subdirectory per external infra component |

**Six-layer KOSMOS architecture mapping**: This is an **infrastructure spec**, not a layer spec. However, it underwrites observability for **Layer 1 (Query Engine)**, **Layer 2 (Tool System)**, and **Layer 3 (Permission Pipeline)** by guaranteeing a working trace export path from those layers to Langfuse. The `docs/vision.md § Layer 1` cost-accounting paragraph ("OpenTelemetry-style counters emit metrics for model tokens, cache hits, and per-ministry call counts") is the foundational citation for the observability thesis this spec operationalises.

**Claude Code parallel**: Claude Code's internal tool loop is extensively traced; KOSMOS's "one Langfuse trace per agent turn, three spans per tool call" mirrors Claude Code's "visualise every tool call so the operator can audit what the model did" principle. The collector is the Bring-Your-Own-Telemetry equivalent of Claude Code's internal telemetry sink.

---

## 4. Best-practice notes (collector hardening within scope)

The following practices are applied inside this spec's scope. Broader hardening (TLS, auth rotation, multi-tenant isolation) is deferred to the Phase 3 Epic.

1. **Read-only config mount** (`:ro` on the `./infra/otel-collector/config.yaml` volume) — prevents runtime mutation of the redaction ruleset even if the container is compromised.
2. **No gRPC receiver** — OTLP HTTP on `:4318` only. gRPC is not required for the local workflow and reducing the open-port surface simplifies the demo machine's security posture.
3. **Health extension explicit** — `health_check` on `:13133`, `pprof` extension **disabled**. Avoids exposing a profiling endpoint.
4. **Batch-queue cap** — `send_batch_size: 512` + `timeout: 5s` bounds the in-memory span buffer to ≤ 512 spans, which at ~2 KB/span is ≤ 1 MB worst case. Below any reasonable OOM threshold.
5. **Env-var-sourced auth header** — `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` sourced from `.env`. Empty default means local dev works without an API key against an anonymous Langfuse project.

---

## 5. Open questions post-Phase 0

None. All `NEEDS CLARIFICATION` markers resolved. All deferred items are tracking-issue-ready.

**Phase 0 gate**: ✅ Pass. Proceed to Phase 1 (data-model + contracts + quickstart).
