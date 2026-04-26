# KOSMOS Brand System

## §1 Brand metaphor

KOSMOS — which stands for Korean Public Service Multi-Agent OS, and whose name doubles as the Korean word 은하계 (galaxy) — is built on a single unifying metaphor: a constellation of ministry APIs, each orbiting a central coordination point, unified for the citizen into one seamless conversational interface. This section defines that metaphor, names its visual primitives, catalogues the ministry satellites that currently orbit the core, and explains why the metaphor survives even in a monochrome text terminal.

### The 은하계 integration metaphor

Korea's digital-government infrastructure is rich but fragmented. Each ministry — 한국도로공사, 기상청, 건강보험심사평가원, 국립중앙의료원, 소방청, 국토교통부 — exposes its own portal, its own authentication flow, its own response format, and its own domain vocabulary. A citizen who needs, say, a route-safety decision that crosses KOROAD traffic data and KMA weather alerts cannot issue a single query; they must know which ministry holds which data, find each portal, understand each API shape, and then synthesize the answers themselves.

KOSMOS resolves this fragmentation. Drawing on the vision stated in [`docs/vision.md`](../vision.md) under "What is original to KOSMOS," the platform's defining contribution is: **bilingual tool discovery across 5,000+ heterogeneous government APIs with inconsistent schemas, unified behind a single conversational window**. The citizen does not learn which ministry runs which API. KOSMOS does the routing.

The 은하계 metaphor encodes this architectural reality into every naming decision in the design system. The platform is the galaxy. Each ministry is a satellite orbiting a central gravitational core. The citizen's query enters the core, which dispatches to whichever satellites are needed and synthesizes their responses into a single answer. Korea's AI Action Plan 공공AX Principle 8 — a single conversational window for all public services — is precisely what this constellation structure delivers. Principle 9 (citizen-facing public-service AI) anchors the requirement that the galaxy metaphor must communicate trust and legibility to a non-technical citizen audience, not just to developers.

This is why the brand metaphor is not decorative. It is a load-bearing description of the system's architecture, expressed in design tokens so that every engineer who reads a color name understands the system they are building.

### Visual element vocabulary

Five brand primitives constitute the KOSMOS visual vocabulary. Each maps to a specific semantic role in the text UI. The canonical visual reference is the onboarding splash screen specified in ADR-006 A-9 ([`../adr/ADR-006-cc-migration-vision-update.md`](../adr/ADR-006-cc-migration-vision-update.md)), which derives from the Claude Code step-registry pattern (`src/components/Onboarding.tsx`) with developer-domain steps replaced by citizen-domain equivalents.

**`kosmosCore`** — the luminous central asterisk rendered at the centre of the onboarding splash. In the SVG assets (`../../assets/kosmos-logo.svg`, `../../assets/kosmos-banner-dark.svg`), this element carries the ring-to-core gradient (`#818cf8` → `#6366f1`). In every subsequent render surface — the status line, the active spinner, the active-ministry indicator — `kosmosCore` tokens mark "this is a single system." The core is never absent while the session is alive; its persistent presence is the visual claim that no matter how many ministries are answering in parallel, the citizen is talking to one thing.

**`orbitalRing`** — the rotating ring that encircles `kosmosCore` during active tool-loop execution. In the splash assets, the ring carries the orbital gradient (`#60a5fa` → `#a78bfa`). In the running TUI, `orbitalRing` tokens are applied to progress indicators and to the border of the permission-gauntlet modal (the PermissionGauntletModal component in `tui/src/components/coordinator/`). The ring's visual rotation is the text-UI affordance for "a ministry adapter call is in flight." When the ring is visible, the citizen knows KOSMOS is working; when it stills, the response is ready. The `orbitalRingShimmer` variant carries the pulsing in-flight state without relying on animation speed — shimmering vs. static encodes the same information glyph-safely.

**`wordmark`** — the literal "KOSMOS" letterform. In the SVG assets (`../../assets/kosmos-banner-dark.svg`, `../../assets/kosmos-banner-light.svg`), the wordmark is rendered in `#e0e7ff` against the navy background. In the TUI, `wordmark` tokens appear in the header and footer rows that provide identity across every screen. The wordmark is the only element that the citizen is expected to recognise as the name of the service they are using.

**`subtitle`** — the "시민의 단일 대화 창" subtitle line that appears directly below the wordmark on the onboarding splash. In the assets, this line renders in `#94a3b8`. Its role is to communicate the KOSMOS mission in Korean to a citizen audience in a single phrase, without requiring the citizen to read documentation. ADR-006 A-9 specifies the subtitle as `KOREAN PUBLIC SERVICE MULTI-AGENT OS` in English on the splash; the Korean-language localisation `시민의 단일 대화 창` (citizen's single conversational window) is the in-session label. The `subtitle` token family anchors all secondary-information lines that carry explanatory text rather than primary identity.

**`agentSatellite{MINISTRY}`** — the per-ministry accent colour family. Each ministry "satellite" has its own colour drawn from the onboarding splash's node palette, making it possible for a citizen to see at a glance which ministry is currently responding. Accent colours are derived from the splash assets (`../../assets/kosmos-logo.svg` satellite-node palette: `#34d399` / `#f472b6` / `#93c5fd` / `#c4b5fd`) and assigned by ministry role. The full list is defined in the Ministry satellite roster below.

### Ministry satellite roster

The following ministries are currently in scope for KOSMOS. Each entry defines the `{MINISTRY}` suffix used in `agentSatellite{MINISTRY}` token names. Adding a new ministry to the KOSMOS adapter tree requires appending a line to this roster **before** any `agentSatellite{MINISTRY}` token can ship — the token-naming grammar defined in §2 defers to this roster as its MinistryCode source of truth (see data-model `§1.7 MetaphorRole`).

- KOROAD — 한국도로공사 (교통사고 위험구간·돌발정보) · accent: `#f472b6` (Epic H #1302 binding; see §4 Palette values)
- KMA — 기상청 (단기예보·주의보) · accent: `#34d399` (Epic H #1302 binding)
- HIRA — 건강보험심사평가원 (병원·약국 검색) · accent: `#93c5fd` (Epic H #1302 binding)
- NMC — 국립중앙의료원 (응급의료센터) · accent: `#c4b5fd` (Epic H #1302 binding)
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
  - `../../assets/kosmos-banner-dark.svg` — wide wordmark + subtitle on the KOSMOS navy background; cited directly in ADR-006 A-9 as the onboarding splash palette extraction source (historical note: an earlier draft of this document referenced `kosmos-logo-dark.svg`, which was never committed — `kosmos-banner-dark.svg` supersedes it per Epic H research R-10)
  - `../../assets/kosmos-banner-dark.svg` — wide wordmark + subtitle on dark background; canonical palette extraction source per ADR-006 A-9
  - `../../assets/kosmos-banner-dark.png` — raster equivalent
  - `../../assets/kosmos-banner-light.svg` — wide wordmark + subtitle on light background; owned by Epic H for the planned light theme
  - `../../assets/kosmos-banner-light.png` — raster equivalent
  - `../../assets/kosmos-org-avatar.svg` — square avatar crop of the core; used in GitHub organisation profile
  - `../../assets/kosmos-org-avatar.png` — raster equivalent
- **Korea AI Action Plan** — 공공AX Principle 8 (단일 대화 창, single conversational window) and Principle 9 (citizen-facing public-service AI) are tracked at the K-AI2026 live dashboard (`hollobit/K-AI2026`, referenced in `docs/vision.md § Reference materials`). Both principles are satisfied structurally by the 은하계 metaphor: Principle 8 by the core-satellite architecture that routes all ministry calls through one conversational interface, and Principle 9 by the citizen-legible branding that communicates trust without requiring technical literacy.

## §2 Token naming doctrine

### Grammar

Every token name in `tui/src/theme/tokens.ts` MUST conform to the following BNF, defined authoritatively in [`../../specs/034-tui-component-catalog/contracts/token-naming-grammar.md`](../../specs/034-tui-component-catalog/contracts/token-naming-grammar.md):

```
TokenName       ::= MetaphorRole Variant?
MetaphorRole    ::= "kosmosCore"
                  | "orbitalRing"
                  | "wordmark"
                  | "subtitle"
                  | "agentSatellite" MinistryCode
                  | "permissionGauntlet"
                  | "planMode"
                  | "autoAccept"
                  | SemanticRole
MinistryCode    ::= "Koroad" | "Kma" | "Hira" | "Nmc" | "Nfa119" | "Geocoding" | …
SemanticRole    ::= "success" | "error" | "warning" | "info" | "text" | "inverseText"
                  | "inactive" | "subtle" | "suggestion" | "remember"
Variant         ::= "Shimmer" | "Muted" | "Hover" | "Active"
                  | "Background" | "Border" | "Dimmed" | "Selected" | …
```

`MetaphorRole` is always camelCase starting with a lowercase letter. `Variant` is always TitleCased (initial capital). Concatenation is direct with no separator: `orbitalRing` + `Shimmer` = `orbitalRingShimmer`, never `orbitalRing_Shimmer` or `orbital-ring-shimmer`.

The `MetaphorRole` vocabulary is a **closed enumerated set** at any given commit. It contains:

- **Structural metaphor roles** — `kosmosCore`, `orbitalRing`, `wordmark`, `subtitle`. These map to the visual affordances of the KOSMOS (은하계) integration metaphor described in §1. A token named `kosmosCore` decorates the central orchestrator visual; `orbitalRing` decorates the tool-loop ring affordance that communicates active agent traversal to the citizen.
- **Ministry satellite roles** — `agentSatellite` followed by a `MinistryCode` suffix drawn from the §1 ministry roster (for example, `agentSatelliteKoroad`, `agentSatelliteHira`, `agentSatelliteKma`). The `MinistryCode` component is TitleCased because it is a proper noun abbreviation, not a `Variant`.
- **Harness state roles** — `permissionGauntlet`, `planMode`, `autoAccept`. These reflect KOSMOS-original surfaces from the permission and autonomy layer (Specs 033 and 027) that have no direct Claude Code analog and therefore receive their own named metaphor roles rather than inheriting a generic color slot.
- **WCAG-aligned semantic slots** — `success`, `error`, `warning`, `info`, `text`, `inverseText`, `inactive`, `subtle`, `suggestion`, `remember`. These carry accessibility-driven meaning that must be stable across theme variants so that WCAG 2.1 AA and 한국 접근성 지침 2.2 contrast guarantees remain verifiable by automated tooling.

The `Variant` vocabulary is **open-ended** subject to owner-Epic approval, but the current canonical set is: `Shimmer`, `Muted`, `Hover`, `Active`, `Background`, `Border`, `Dimmed`, `Selected`. A new `Variant` value requires an ADR amendment or an approved PR comment from the Brand Guardian before it ships.

---

### Banned patterns

The following seven rules are enforced by the Brand Guardian grep CI gate (see [`../../specs/034-tui-component-catalog/contracts/grep-gate-rules.md`](../../specs/034-tui-component-catalog/contracts/grep-gate-rules.md)) on every PR that touches `tui/src/theme/**` or `docs/design/brand-system.md`. Each rule applies to newly added identifiers in the type surface of `tokens.ts`; the allow-listed legacy identifiers are exempt (see Exceptions below).

| Rule ID | Regex | Error message | Why it is banned |
|---------|-------|---------------|------------------|
| BAN-01 | `^claude[A-Za-z0-9_]*$` | `Banned token: CC-legacy '{name}'. See brand-system.md §2 — use an 'orbitalRing*' or ministry-specific name instead.` | Leaks Claude Code brand identity into the KOSMOS citizen surface, which is an original KOSMOS harness, not a Claude Code product. Any visual that previously carried "claude" framing must be renamed to its KOSMOS metaphor equivalent under Deferred Items row 10. |
| BAN-02 | `^clawd[A-Za-z0-9_]*$` | `Banned token: leaked-source prefix '{name}'. Remove; rename under KOSMOS metaphor vocabulary.` | The `clawd` prefix is a CC-internal source artifact that leaked into the TUI during the initial Ink port (Spec 287). It carries no semantic meaning and directly exposes implementation internals of a third-party codebase. |
| BAN-03 | `^anthropic[A-Za-z0-9_]*$` | `Banned token: vendor-specific '{name}'. KOSMOS is not an Anthropic product.` | KOSMOS is powered by LG AI Research's EXAONE via FriendliAI Serverless. Encoding the name of an unrelated vendor into the public type surface creates false affiliation, confuses future Brand Guardian reviewers, and contradicts the KOSMOS citizen-domain framing established in ADR-006 A-9. |
| BAN-04 | `^(primary\|secondary\|tertiary)$` | `Banned token: content-free '{name}'. Use a semantic role from brand-system.md §1 (e.g., 'kosmosCore', 'orbitalRing', or a ministry satellite).` | In a multi-ministry context, the question "which ministry is primary" is a live, session-dependent answer — it changes based on which tool the coordinator is currently routing to. A static token named `primary` conveys no useful information to a downstream component author or a Brand Guardian reviewer. |
| BAN-05 | `^accent[0-9]+$` | `Banned token: numeric suffix '{name}'. Tokens must describe semantic role, not ordinal.` | Ordinal naming (`accent1`, `accent2`) is a holdover from single-brand design systems where colors are enumerated rather than named for meaning. In the KOSMOS ministry-satellite model, every accent has a specific metaphor role (kosmosCore, orbitalRing, a ministry satellite) and that role should be stated, not numbered. |
| BAN-06 | `^mainColor$` | `Banned token: '{name}' conveys no semantic intent.` | The identifier `mainColor` says nothing about what the color represents, which theme layer it belongs to, or which visual element it styles. It is indistinguishable from a placeholder and violates the §2 principle that a token name must be self-documenting to a Brand Guardian reviewer with no context. |
| BAN-07 | `^(background\|foreground)$` | `Banned token: standalone '{name}'. Qualify with a role (e.g., 'orbitalRingBackground', 'kosmosCoreForeground').` | Unqualified `background` and `foreground` are ambiguous in a multi-layer TUI where the orbital ring, the permission gauntlet modal, ministry satellite rows, and system chrome each maintain independent background layers. Standalone names create merge conflicts when Epic H authors palette values and cannot be mapped to a specific semantic surface for contrast-ratio verification. |

---

### Exceptions

Three categories of identifiers are exempt from the banned-pattern rules.

**WCAG-aligned semantic slots.** The names `success`, `error`, `warning`, and `info` would superficially resemble "content-free" tokens under a strict reading of BAN-04, but they are explicitly permitted because their meaning is accessibility-driven rather than brand-driven. These names are standardized across design systems and screen-reader conventions so that assistive technologies, automated contrast checkers, and Epic H palette authors can reason about them without inspecting the component tree. Renaming `error` to `kosmosError` would break this convention without adding semantic value. The full set of permitted semantic slots is: `success`, `error`, `warning`, `info`, `text`, `inverseText`, `inactive`, `subtle`, `suggestion`, `remember`.

**CC-legacy allow-list.** The 69 token identifiers currently in `tui/src/theme/tokens.ts` (enumerated in `artifacts/existing-tokens.txt` as of 2026-04-20) are allow-listed in `tui/src/theme/.brand-guardian-allowlist.txt` at the commit where the grep gate workflow ships. The gate tests only **newly added** identifiers in a PR's diff against the type surface. Pre-existing allow-listed names — including BAN-01 violations such as `claudeShimmer`, `claudeBlue_FOR_SYSTEM_SPINNER`, and `briefLabelClaude`, and BAN-02 violations such as `clawd_body` and `clawd_background` — pass silently. The mass rename of all 69 legacy identifiers to KOSMOS metaphor vocabulary is tracked as Deferred Items row 10 under Epic M #1310 and will be executed in a dedicated PR after the token naming infrastructure stabilizes. The Sonnet teammate implementing the workflow MUST regenerate the allow-list from the live `tokens.ts` at implementation time rather than copying the stale list from the contracts directory.

**Ministry satellite extensions.** New `agentSatellite{MINISTRY}` token names are permitted provided the corresponding `MinistryCode` already appears in the §1 ministry roster of `docs/design/brand-system.md`. A `MinistryCode` not yet in the §1 roster requires a single-line PR against §1 first; the grep gate treats the §1 roster as its live source of truth and immediately accepts the new satellite token name after the §1 PR merges, with no §2 edit required.

---

### Ministry roster pointer

The definitive list of `agentSatellite{MINISTRY}` extensions lives in [§1 Brand metaphor](#§1-brand-metaphor) of this document. Section §2 only restates the lookup pattern: when a new ministry enters the §1 roster, the grep gate immediately begins accepting its corresponding token names without any change to §2 prose or the BAN rules. This design keeps §2 as a stable normative contract whose content changes only when the token naming grammar itself changes, not merely because a new ministry joins the platform. Authors who wish to extend the ministry roster must open a PR that edits §1 exclusively; attempting to bypass §1 by introducing a new `agentSatellite{MINISTRY}` token without a §1 roster entry will cause the grep gate to reject the identifier as an unrecognized `MetaphorRole`.

---

### Brand Guardian review contract

Every PR that touches `tui/src/theme/**` or `docs/design/brand-system.md` triggers the Brand Guardian grep CI gate. The gate implementation is a post-verdict Task under Epic M (Deferred Items row 11) that creates `.github/workflows/brand-guardian.yml` running `scripts/lint-tokens.mjs` or equivalent. The gate emits a GitHub Check Run whose summary includes a formatted failure table with each violating identifier, its line number in the PR diff, the matching BAN rule ID, and the corresponding error message from the table above.

The full gate logic is specified in [`../../specs/034-tui-component-catalog/contracts/grep-gate-rules.md`](../../specs/034-tui-component-catalog/contracts/grep-gate-rules.md) §4. In summary: the gate parses the `tokens.ts` type surface, loads the allow-list, and for each newly added identifier tests it against BAN-01 through BAN-07 in sequence. If any rule matches, the gate exits with a non-zero status, blocking the PR merge.

A Brand Guardian reviewer may manually grant an exception to a specific identifier on a case-by-case basis. When doing so, the reviewer MUST leave a PR comment that (a) names the exception category from the Exceptions subsection above, (b) explains why the identifier qualifies, and (c) states whether the exception is temporary (pending a Deferred rename) or permanent (the identifier is a legitimate semantic slot). The PR comment serves as the audit trail; there is no automated override mechanism — the Brand Guardian must update the allow-list file directly if the exception is meant to persist across the gate's diff-based check.

The gate does NOT validate color hex values (that responsibility belongs to Epic H #1302), does NOT check contrast ratios (handled by a separate accessibility gate), and does NOT run outside PR events — there is no scheduled or push-triggered run.

---

### Rejection worked examples

The following three cases demonstrate how §2 subsections apply to simulated ad-hoc token proposals. These cases are the normative fixtures for the SC-012 test referenced in the spec.

**Proposal: `primary`**
Rejected by BAN-04 (`^(primary|secondary|tertiary)$`). Error message from the gate: "Content-free token 'primary'. Use a semantic role from brand-system.md §1 (e.g., 'kosmosCore', 'orbitalRing', or a ministry satellite)." The Brand Guardian review contract subsection above explains the process: the author receives a failing Check Run, must rename the identifier to a `MetaphorRole` drawn from §1, and may not bypass the gate without a formal exception comment from a Brand Guardian reviewer.

**Proposal: `accent1`**
Rejected by BAN-05 (`^accent[0-9]+$`). Error message from the gate: "Numeric-suffix token 'accent1'. Tokens must describe semantic role, not ordinal." The correct replacement depends on intent: if the color decorates the orbital ring in an active state, the correct name is `orbitalRingActive`; if it decorates a ministry satellite, it should be `agentSatelliteKoroad` or equivalent. The numeric suffix carries no information that survives a palette refactor.

**Proposal: `claudeShimmer` (as a new addition)**
Rejected by BAN-01 (`^claude[A-Za-z0-9_]*$`) when introduced as a new identifier. Error message from the gate: "CC-legacy prefix 'claudeShimmer'. See brand-system.md §2 — use an 'orbitalRing*' or ministry-specific name instead." However, note that `claudeShimmer` already exists in the current allow-list (it appears in `artifacts/existing-tokens.txt` as one of the 69 legacy identifiers). If a PR adds `claudeShimmer` and it is already in `.brand-guardian-allowlist.txt`, the gate passes silently. The gate only flags it if it appears as a genuinely new addition — for example, if a PR deletes the existing entry and then re-adds it under a different type alias. The mass rename of `claudeShimmer` to `orbitalRingShimmer` (its semantic equivalent) is tracked under Deferred Items row 10.

---

### Future-proofing process

When a new metaphor role becomes necessary — for example, if a Phase 3 Epic introduces a `plugin` visual affordance or a `skill` orchestration layer with its own color identity — the process for extending §2 is as follows:

1. **Author an ADR** amending ADR-006, specifically the A-9 brand vocabulary section. The ADR must justify why an existing `MetaphorRole` cannot serve the new role, describe the visual or semantic distinction the new name communicates, and receive approval from the Lead reviewer before any downstream work begins.

2. **Extend `contracts/token-naming-grammar.md`** by adding the new `MetaphorRole` value to the `MetaphorRole` enumeration in §1 of that contract file. This change is the machine-readable authoritative source from which the grep gate's parser derives the set of valid role names.

3. **Edit §2 of this document** to document the new role: its purpose, which visual surface or interaction state it decorates, and its valid `Variant` combinations. This §2 edit is the human-readable counterpart to the grammar contract update.

In-place §2 edits that introduce a new `MetaphorRole` WITHOUT a corresponding ADR are rejected by code review. The ADR requirement exists because metaphor role vocabulary is architectural: adding a new named role implies a new visual affordance in the TUI, which has downstream consequences for Epic H (palette), Epic J (typography), Epic L (notifications), and any ministry Epic that inherits the role as a satellite extension. The ADR surfaces these cross-Epic dependencies before implementation begins rather than after a merge conflict emerges.

New `Variant` values — as opposed to new `MetaphorRole` values — require a lighter-weight process: an approved PR comment from the Brand Guardian confirming the variant is semantically distinct from the existing eight canonical variants. The Brand Guardian may approve the new variant directly in the PR without an ADR, provided the variant name is TitleCased and does not collide with any BAN rule. If the variant name becomes widely adopted across three or more `MetaphorRole` contexts, it should be added to the canonical `Variant` list in `contracts/token-naming-grammar.md` in a follow-up PR.

## §3 Logo usage

**Owner: Epic H #1302** — populated by `specs/035-onboarding-brand-port/` (ADR-006 A-9 binding).

### §3.1 · Primary wordmark asset

The KOSMOS wordmark + subtitle composition is rendered from a single SVG source:

- `../../assets/kosmos-banner-dark.svg` — authoritative wide-format wordmark on the KOSMOS navy `#0a0e27` background. This is the palette-extraction source cited by ADR-006 A-9 and the only asset that carries the canonical KOSMOS hex values.
- `../../assets/kosmos-logo.svg` — compact square logo (core + ring composition); also carries the 16-hex superset from which shimmer variants were drawn per research R-2.
- `../../assets/kosmos-banner-light.svg`, `../../assets/kosmos-banner-light.png` — light-theme variants owned by Epic H for the deferred light-theme work.

### §3.2 · Clear-space rule

The wordmark must have clear space of at least one glyph-cell on every side. In the TUI this is enforced by wrapping the wordmark in an Ink `<Box flexDirection="column" alignItems="center">` with a `marginTop={1}` and `marginBottom={1}` — the splash composition in `tui/src/components/onboarding/LogoV2/LogoV2.tsx` models the canonical spacing.

### §3.3 · Forbidden transformations

- Never render the wordmark in any colour other than `wordmark` token (`#e0e7ff` on dark; light theme deferred).
- Never insert punctuation or whitespace between the letters `K O S M O S` — the letterform is a single identity.
- Never substitute `*` for a decorative glyph — the kosmosCore asterisk is the load-bearing metaphor.

## §4 Palette values

**Owner: Epic H #1302** — normative reference for every KOSMOS brand token.

### §4.1 · Primary dark palette (`tui/src/theme/dark.ts`)

| Token | Primary hex | RGB | Ministry binding | Measured contrast vs `#0a0e27` | Pair kind |
|---|---|---|---|---|---|
| `background` | `#0a0e27` | `rgb(10,14,39)` | — | — (self) | — |
| `kosmosCore` | `#6366f1` | `rgb(99,102,241)` | — | see [`contrast-measurements.md`](./contrast-measurements.md) | non-text |
| `kosmosCoreShimmer` | `#a5b4fc` | `rgb(165,180,252)` | — | see [`contrast-measurements.md`](./contrast-measurements.md) | non-text |
| `orbitalRing` | `#60a5fa` | `rgb(96,165,250)` | — | see [`contrast-measurements.md`](./contrast-measurements.md) | non-text |
| `orbitalRingShimmer` | `#c7d2fe` | `rgb(199,210,254)` | — | see [`contrast-measurements.md`](./contrast-measurements.md) | non-text |
| `wordmark` | `#e0e7ff` | `rgb(224,231,255)` | — | see [`contrast-measurements.md`](./contrast-measurements.md) | body |
| `subtitle` | `#94a3b8` | `rgb(148,163,184)` | — | see [`contrast-measurements.md`](./contrast-measurements.md) | body |
| `agentSatelliteKoroad` | `#f472b6` | `rgb(244,114,182)` | KOROAD (한국도로공사) | see [`contrast-measurements.md`](./contrast-measurements.md) | body |
| `agentSatelliteKma` | `#34d399` | `rgb(52,211,153)` | KMA (기상청) | see [`contrast-measurements.md`](./contrast-measurements.md) | body |
| `agentSatelliteHira` | `#93c5fd` | `rgb(147,197,253)` | HIRA (건강보험심사평가원) | see [`contrast-measurements.md`](./contrast-measurements.md) | body |
| `agentSatelliteNmc` | `#c4b5fd` | `rgb(196,181,253)` | NMC (국립중앙의료원) | see [`contrast-measurements.md`](./contrast-measurements.md) | body |

### §4.2 · Contrast authority

The authoritative measured contrast ratios for every palette pair live in [`contrast-measurements.md`](./contrast-measurements.md), machine-regenerated by `scripts/compute-contrast.mjs` on every palette change. All Epic H-introduced tokens pass the WCAG 2.1 thresholds: body text ≥ 4.5:1, non-text ≥ 3:1. Preserve-set tokens whose original value fell below threshold under the new `#0a0e27` background were raised per FR-011 (see commit diff on `subtle` / `diffAdded` / `diffRemoved`).

### §4.3 · Palette provenance

Every primary hex listed above was extracted from `../../assets/kosmos-logo.svg` and `../../assets/kosmos-banner-dark.svg`. Shimmer-variant hexes come from the same SVG's 16-hex superset per research R-2. Ministry accent assignments (KOROAD ↔ `#f472b6`, etc.) are binding as of Epic H #1302; §1's roster entries cross-reference this table.

## §5 Typography scale

**Owner: Epic H #1302**

### §5.1 · Font stack (Hangul-safe monospace)

The TUI does not choose a font — it inherits the user's terminal font. However, KOSMOS components assume a monospace terminal that renders:

- Hangul syllables (AC00–D7A3) as width-2 glyphs — matching the East-Asian wide-char convention.
- Unicode block-drawing characters (U+2500–U+257F) for the orbital-ring frame.
- The U+002A `*` asterisk in the `kosmosCore` token.

For width computation across Hangul + CJK + ASCII mixed strings, every KOSMOS component uses `tui/src/ink/stringWidth.ts` (ported from CC per Spec 287) rather than rolling its own width pass. This is the single source of truth for terminal grid alignment and must not be duplicated inside a component.

### §5.2 · Terminal font recommendations

The following fonts are verified to render the KOSMOS splash correctly. They are recommendations — not requirements — and are listed for the citizen-facing onboarding handout:

- D2Coding (Korean-community monospace, free)
- Sarasa Mono K (CJK-wide monospace, free)
- JetBrains Mono + Hangul fallback (developer-leaning, free)
- Terminal.app default (`Menlo`) + the OS's Hangul fallback (Mac)

Missing-glyph fallback: when the terminal renders `*` as a visibly-square replacement glyph, the splash still communicates; the reduced-motion branch uses the same glyph.

## §6 Spacing / grid

**Owner: Epic H #1302**

### §6.1 · Cell-grid model

KOSMOS composes within a fixed character grid. One column = one cell of ASCII width; one Hangul syllable = two cells. All component layouts are expressed in cells using Ink's `Box` props (`width`, `height`, `marginX`, `paddingX`, etc.). There is no pixel grid — the measurement primitive is the cell.

### §6.2 · Canonical splash dimensions

- Full splash (≥ 80 columns): centred composition, `kosmosCore` asterisk cluster (width 5, height 3), orbital-ring frame (inner width 13), wordmark row (width 6), subtitle row (width up to 60). Detailed geometry lives in `tui/src/components/onboarding/LogoV2/logoV2Utils.ts::calculateLayoutDimensions`.
- Condensed (50–79 columns): single-line `CondensedLogo` (prefix asterisk + wordmark + segments).
- Fallback (< 50 columns): `KOSMOS — 한국 공공서비스 대화창` on one line.

### §6.3 · Hangul-syllable spacing

Hangul syllables are rendered at width 2. When mixing Hangul with ASCII digits / English codes (e.g. `한국도로공사 (KOROAD)`), the terminal places the ASCII at width 1, so alignment must be computed with `stringWidth` before the layout pass. KOSMOS layouts never hardcode column offsets — they compute each line's width and use `Box` `flexDirection` + `justifyContent` to position it. This is why Hangul labels do not break at wider / narrower terminal widths.

## §7 Motion

**Owner: Epic H #1302**

### §7.1 · Shimmer frame budget

Every shimmering component in KOSMOS cycles at **6 fps** — a 166 ms tick interval — matching the CC `useShimmerAnimation.ts` cadence. Faster rates flicker on low-quality terminals; slower rates drop below the "active" perceptual threshold. The shimmer cadence is shared by `AnimatedAsterisk`, `KosmosCoreIcon`, and any future shimmering surface.

### §7.2 · Reduced-motion gate (`useReducedMotion`)

Every shimmering component reads `tui/src/hooks/useReducedMotion.ts`, which returns `{ prefersReducedMotion: true }` when either `NO_COLOR` or `KOSMOS_REDUCED_MOTION` is set in the environment. When reduced-motion is active:

- The `setInterval` is not started (zero re-render pressure).
- The component renders its static-variant glyph only (e.g. `*` in `kosmosCore` without cycling to `kosmosCoreShimmer`).
- The visual information is preserved — colour + glyph still communicate the state — only the animation frame is suppressed.

`NO_COLOR` equivalence means that users who have already opted out of terminal colours via the no-color.org convention automatically get reduced-motion too. This pairing is documented in `docs/tui/accessibility-gate.md § 1.1`.

### §7.3 · Orbital-ring pulsing

The orbital-ring frame in `LogoV2.tsx` full-mode is rendered as a static frame; the ring's "activity" is conveyed by the `AnimatedAsterisk` shimmer at its centre rather than by animating the ring itself. Animating the ring characters would require terminal redraws at every tick — the KOSMOS design avoids this cost by making the core the only animated element.

## §8 Voice & tone

**Owners: Epic H #1302 + Epic K #1308**

This section is intentionally a placeholder until Epic H or Epic K enters its Spec Kit cycle. Do not edit under Epic M — edits land as part of the owning Epic's PR. See Epic M #1310 FR-014 for the scope rule.

## §9 Iconography

**Owner: Epic H #1302**

### §9.1 · Core glyph — U+002A asterisk

KOSMOS uses a standard ASCII asterisk (`*`, U+002A) as its core glyph. The choice is deliberate:

- The asterisk is present in every terminal font; there is no fallback to worry about.
- Its five-point geometry evokes the orbital-core metaphor without requiring graphics.
- It pairs naturally with block-drawing characters (U+2500–U+257F) for the orbital ring frame.

The asterisk is never substituted by a stylised glyph (e.g. ✦, ✴, ✷). Any visual elaboration happens via colour cycling (`kosmosCoreShimmer`) rather than glyph substitution. This keeps the KOSMOS brand legible on every terminal, including low-quality ones that replace uncommon glyphs with a square.

### §9.2 · Asterisk cluster (`WelcomeV2`)

The welcome screen renders a 3×3 asterisk cluster with a centre `●` (U+25CF, BLACK CIRCLE) in `kosmosCoreShimmer`:

```
  *  *  *
 *  ●  *
  *  *  *
```

The `●` is the only non-asterisk glyph in the cluster; it represents the citizen's "here" position within the galaxy metaphor. Under reduced-motion the `●` is rendered in `kosmosCore` (no shimmer).

### §9.3 · Ministry availability indicators

The feed component uses U+25CF `●` (available) and U+25CB `○` (unavailable) as ministry-status glyphs, with each row's indicator carrying the `agentSatellite{MINISTRY}` accent. These glyphs are universally supported in terminal fonts and communicate availability glyph-safely even on monochrome terminals.

### §9.4 · Korean-safe fallback policy

Any future KOSMOS glyph added to the design system must pass three checks before landing:

1. Present in the Unicode BMP (not in a supplementary plane).
2. Renders width-1 on standard terminal fonts (non-wide-char ASCII-equivalent) OR clearly documented as width-2 for Hangul-family inclusion.
3. Has a reduced-motion fallback (either static or replaced with a simpler primitive).

## §10 Component usage guidelines

**Owners: all design-concerned Epics (B/C/D/E/H/I/J/K/L/M)**

Each downstream Epic appends a dated H3 subheading as its components ship. This section is a collaborative appendix; no single Epic may rewrite prior entries. See Epic M #1310 FR-014 + the §10 collab tracker Task for the contribution contract.
