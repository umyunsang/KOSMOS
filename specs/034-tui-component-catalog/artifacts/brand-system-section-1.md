KOSMOS — which stands for Korean Public Service Multi-Agent OS, and whose name doubles as the Korean word 은하계 (galaxy) — is built on a single unifying metaphor: a constellation of ministry APIs, each orbiting a central coordination point, unified for the citizen into one seamless conversational interface. This section defines that metaphor, names its visual primitives, catalogues the ministry satellites that currently orbit the core, and explains why the metaphor survives even in a monochrome text terminal.

### The 은하계 integration metaphor

Korea's digital-government infrastructure is rich but fragmented. Each ministry — 한국도로공사, 기상청, 건강보험심사평가원, 국립중앙의료원, 소방청, 국토교통부 — exposes its own portal, its own authentication flow, its own response format, and its own domain vocabulary. A citizen who needs, say, a route-safety decision that crosses KOROAD traffic data and KMA weather alerts cannot issue a single query; they must know which ministry holds which data, find each portal, understand each API shape, and then synthesize the answers themselves.

KOSMOS resolves this fragmentation. Drawing on the vision stated in [`docs/vision.md`](../vision.md) under "What is original to KOSMOS," the platform's defining contribution is: **bilingual tool discovery across 5,000+ heterogeneous government APIs with inconsistent schemas, unified behind a single conversational window**. The citizen does not learn which ministry runs which API. KOSMOS does the routing.

The 은하계 metaphor encodes this architectural reality into every naming decision in the design system. The platform is the galaxy. Each ministry is a satellite orbiting a central gravitational core. The citizen's query enters the core, which dispatches to whichever satellites are needed and synthesizes their responses into a single answer. Korea's AI Action Plan 공공AX Principle 8 — a single conversational window for all public services — is precisely what this constellation structure delivers. Principle 9 (citizen-facing public-service AI) anchors the requirement that the galaxy metaphor must communicate trust and legibility to a non-technical citizen audience, not just to developers.

This is why the brand metaphor is not decorative. It is a load-bearing description of the system's architecture, expressed in design tokens so that every engineer who reads a color name understands the system they are building.

### Visual element vocabulary

Five brand primitives constitute the KOSMOS visual vocabulary. Each maps to a specific semantic role in the text UI. The canonical visual reference is the onboarding splash screen specified in ADR-006 A-9 ([`../adr/ADR-006-cc-migration-vision-update.md`](../adr/ADR-006-cc-migration-vision-update.md)), which derives from the Claude Code step-registry pattern (`src/components/Onboarding.tsx`) with developer-domain steps replaced by citizen-domain equivalents.

**`kosmosCore`** — the luminous central asterisk rendered at the centre of the onboarding splash. In the SVG assets (`../../assets/kosmos-logo.svg`, `../../assets/kosmos-logo-dark.svg`), this element carries the ring-to-core gradient (`#818cf8` → `#6366f1`). In every subsequent render surface — the status line, the active spinner, the active-ministry indicator — `kosmosCore` tokens mark "this is a single system." The core is never absent while the session is alive; its persistent presence is the visual claim that no matter how many ministries are answering in parallel, the citizen is talking to one thing.

**`orbitalRing`** — the rotating ring that encircles `kosmosCore` during active tool-loop execution. In the splash assets, the ring carries the orbital gradient (`#60a5fa` → `#a78bfa`). In the running TUI, `orbitalRing` tokens are applied to progress indicators and to the border of the permission-gauntlet modal (the PermissionGauntletModal component in `tui/src/components/coordinator/`). The ring's visual rotation is the text-UI affordance for "a ministry adapter call is in flight." When the ring is visible, the citizen knows KOSMOS is working; when it stills, the response is ready. The `orbitalRingShimmer` variant carries the pulsing in-flight state without relying on animation speed — shimmering vs. static encodes the same information glyph-safely.

**`wordmark`** — the literal "KOSMOS" letterform. In the SVG assets (`../../assets/kosmos-banner-dark.svg`, `../../assets/kosmos-banner-light.svg`), the wordmark is rendered in `#e0e7ff` against the navy background. In the TUI, `wordmark` tokens appear in the header and footer rows that provide identity across every screen. The wordmark is the only element that the citizen is expected to recognise as the name of the service they are using.

**`subtitle`** — the "시민의 단일 대화 창" subtitle line that appears directly below the wordmark on the onboarding splash. In the assets, this line renders in `#94a3b8`. Its role is to communicate the KOSMOS mission in Korean to a citizen audience in a single phrase, without requiring the citizen to read documentation. ADR-006 A-9 specifies the subtitle as `KOREAN PUBLIC SERVICE MULTI-AGENT OS` in English on the splash; the Korean-language localisation `시민의 단일 대화 창` (citizen's single conversational window) is the in-session label. The `subtitle` token family anchors all secondary-information lines that carry explanatory text rather than primary identity.

**`agentSatellite{MINISTRY}`** — the per-ministry accent colour family. Each ministry "satellite" has its own colour drawn from the onboarding splash's node palette, making it possible for a citizen to see at a glance which ministry is currently responding. Accent colours are derived from the splash assets (`../../assets/kosmos-logo.svg` satellite-node palette: `#34d399` / `#f472b6` / `#93c5fd` / `#c4b5fd`) and assigned by ministry role. The full list is defined in the Ministry satellite roster below.

### Ministry satellite roster

The following ministries are currently in scope for KOSMOS. Each entry defines the `{MINISTRY}` suffix used in `agentSatellite{MINISTRY}` token names. Adding a new ministry to the KOSMOS adapter tree requires appending a line to this roster **before** any `agentSatellite{MINISTRY}` token can ship — the token-naming grammar defined in §2 defers to this roster as its MinistryCode source of truth (see data-model `§1.7 MetaphorRole`).

- KOROAD — 한국도로공사 (교통사고 위험구간·돌발정보) · accent: road-safety orange
- KMA — 기상청 (단기예보·주의보) · accent: weather blue
- HIRA — 건강보험심사평가원 (병원·약국 검색) · accent: health teal
- NMC — 국립중앙의료원 (응급의료센터) · accent: emergency red
- 119 NFA — 소방청 (구급·구조 긴급상황) · accent: fire-service red-orange
- Geocoding — 국토교통부 (주소·좌표 변환) · accent: geospatial grey-blue

The specific colour values assigned to each accent are owned by Epic H #1302 (§4 Palette values). This roster defines only the **names** and the **semantic roles** — consistent with the FR-010 requirement that Epic M defines the token name surface only, and Epic H defines palette values.

Every PR that introduces a new `agentSatellite{MINISTRY}` variant in `tui/src/theme/tokens.ts` MUST first open a PR that appends the ministry to this roster. The grep-based CI gate specified under FR-011 enforces this: a token whose `{MINISTRY}` suffix is not present in the roster fails the check. This invariant is the mechanism that keeps the data-model closed set (`§1.7 MetaphorRole`) in sync with the shipped token surface.

### Why the metaphor matters for a text UI

A terminal does not render orbital rings as SVG arcs, or satellite nodes as glowing circles. The Ink + React + Bun TUI stack (ADR-003) draws in a fixed character grid. The metaphor could seem purely decorative — something to describe in a brand deck, irrelevant to production code.

It is not. In a text UI, the metaphor survives entirely through naming, and naming determines how every engineer who reads the token list understands the system they are building.

When an engineer reads `orbitalRingShimmer`, the name alone carries the architectural story: the shimmering border is the tool-loop call-in-flight affordance. The engineer does not need to read the brand-system documentation to know that this token belongs on progress indicators and permission-gauntlet borders — the metaphor embedded in the name tells them. When they read `agentSatelliteKoroad`, they know the accent colour is "KOROAD is answering right now." When they read `kosmosCore`, they know the element is the persistent "single system" anchor. The entire orchestration narrative is recoverable from the token list alone.

This is the critical difference between a token naming system grounded in a metaphor and one grounded in visual descriptions (`primary`, `accent1`, `background`) or vendor names (`claudeBlue`). Visual descriptions encode only the appearance, and appearances change across themes. Vendor names encode the wrong domain — KOSMOS is not a Claude product. A metaphor-grounded name encodes the **purpose** of the element across all rendering contexts, all themes, and all future component additions.

The Korea AI Action Plan 공공AX Principle 9 adds a further constraint: citizen-facing AI must communicate legibly and build trust with a non-technical audience. A citizen who sees a shimmering border and a coloured accent on a status line is receiving a designed communication: "something is happening, and 기상청 is involved." That communication is only coherent if every component that contributes to it draws from the same metaphor-grounded palette. Token names are the enforcement mechanism for that coherence.

### Permanent cross-references

- **ADR-006 A-9** ([`../adr/ADR-006-cc-migration-vision-update.md`](../adr/ADR-006-cc-migration-vision-update.md)) — normative anchor for the onboarding splash palette, step sequence, and the requirement to replace the placeholder `dark.ts` background token (`rgb(0,204,204)`) with the KOSMOS navy (`#0a0e27`) in the same PR that ports the onboarding splash component.
- **Brand assets on disk** — the following files are present under `/Users/um-yunsang/KOSMOS/assets/` and serve as the authoritative source of palette values for Epic H #1302:
  - `../../assets/kosmos-logo.svg` — primary logo (light background)
  - `../../assets/kosmos-logo.png` — raster equivalent
  - `../../assets/kosmos-logo-dark.svg` — logo optimised for the KOSMOS navy dark background; cited directly in ADR-006 A-9 as the onboarding splash source
  - `../../assets/kosmos-banner-dark.svg` — wide wordmark + subtitle on dark background; canonical palette extraction source per ADR-006 A-9
  - `../../assets/kosmos-banner-dark.png` — raster equivalent
  - `../../assets/kosmos-banner-light.svg` — wide wordmark + subtitle on light background; owned by Epic H for the planned light theme
  - `../../assets/kosmos-banner-light.png` — raster equivalent
  - `../../assets/kosmos-org-avatar.svg` — square avatar crop of the core; used in GitHub organisation profile
  - `../../assets/kosmos-org-avatar.png` — raster equivalent
- **Korea AI Action Plan** — 공공AX Principle 8 (단일 대화 창, single conversational window) and Principle 9 (citizen-facing public-service AI) are tracked at the K-AI2026 live dashboard (`hollobit/K-AI2026`, referenced in `docs/vision.md § Reference materials`). Both principles are satisfied structurally by the 은하계 metaphor: Principle 8 by the core-satellite architecture that routes all ministry calls through one conversational interface, and Principle 9 by the citizen-legible branding that communicates trust without requiring technical literacy.
