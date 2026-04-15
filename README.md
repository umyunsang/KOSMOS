<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/kosmos-banner-dark.svg"/>
  <source media="(prefers-color-scheme: light)" srcset="assets/kosmos-banner-light.svg"/>
  <img alt="KOSMOS" src="assets/kosmos-banner-light.svg" width="600"/>
</picture>

# KOSMOS

**KO**rean public **S**erivce **M**ulti-agent **O**rchestration **S**ystem

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-purple.svg)](CODE_OF_CONDUCT.md)
[![GitHub Discussions](https://img.shields.io/badge/discussions-join-blueviolet)](https://github.com/umyunsang/KOSMOS/discussions)

A conversational multi-agent harness that orchestrates data.go.kr's 5,000+ public APIs around LG AI Research's K-EXAONE through an agentic tool loop.

> Academic R&D project. Not affiliated with Anthropic, LG AI Research, or the Korean government.

## Vision

Turn the 5,000+ fragmented public APIs on data.go.kr into a single conversational interface where citizens can resolve cross-ministry civil affairs (민원) in natural language — route safety, emergency services, welfare benefits, residence transfer, and more.

## Citizen Scenarios

Five end-to-end flows the platform must handle for the vision to be considered met:

```text
시민:   "내일 부산에서 서울 가는데, 안전한 경로 추천해줘"
KOSMOS: KOROAD accident data + KMA weather alerts + road-risk index
        → "Gyeongbu Expressway Daejeon-Cheonan section: high risk,
           fog advisory. Suggest Jungbu-Naeryuk detour."

시민:   "아이가 열이 나는데 근처 야간 응급실 어디야?"
KOSMOS: 119 emergency API + HIRA hospital info
        → Available ERs ranked by location + current wait time

시민:   "이사 준비 중인데, 전입신고랑 자동차 주소변경이랑
        건강보험 주소변경 다 해야 하는데"
KOSMOS: Coordinator dispatches Civil-affairs / Transport / Welfare workers
        → "전입신고 선행 → 자동차·건강보험 병렬"
```

Citizens never learn which ministry runs which API. **KOSMOS does the routing.**

## Architecture

KOSMOS transfers six architectural layers from Claude Code into the public-service domain:

<img src="docs/diagrams/kosmos_6_layer_architecture.svg" alt="KOSMOS 6-Layer Architecture" width="100%">

The lineage of each layer:

| Layer | Claude Code Origin | KOSMOS Adaptation |
|---|---|---|
| **Query Engine** | `while(true)` tool loop + 5-stage preprocessing | Civil-affairs state machine with ministry routing |
| **Tool System** | `buildTool()` factory + Partition-Sort cache strategy | `buildGovAPI()` adapters for data.go.kr endpoints |
| **Permission Pipeline** | 7-step gauntlet with bypass-immune checks | Citizen authentication + PII protection layers |
| **Agent Swarms** | File-based mailbox IPC + Coordinator synthesis | Ministry-specialist agents over message queue |
| **Context Assembly** | CLAUDE.md 6-tier memory + per-turn attachments | `CITIZEN.md` profile + live API status attachments |
| **Error Recovery** | `withRetry` with 429/529/401 matrix | Public-API outage fallback + cross-ministry verification |

For deep dives into the Query Engine loop, the Permission Pipeline gauntlet, and the Agent Swarm coordination model, see [`docs/presentation.md`](docs/presentation.md) and [`docs/vision.md`](docs/vision.md).

## Model Stack

- **Orchestrator** — K-EXAONE 236B (reasoning mode) for multi-agent synthesis and long-context civil-affairs flows
- **Workers** — EXAONE 4.5 33B (non-reasoning) for single API calls, OCR, and fast response
- **Router / Classifier** — EXAONE 4.0 1.2B for intent classification and ministry routing

## Roadmap

- **Phase 1 — Prototype** ✅ — FriendliAI Serverless + 10 high-value APIs + single query engine + CLI. Scenario 1 (route safety) end-to-end working with **33/33 live tests passing**.
- **Phase 2 — Swarm** — Ministry-specialist agents, mailbox IPC, multi-API synthesis. Scenarios 1–3.
- **Phase 3 — Production** — Full permission pipeline, identity verification, audit logging, all five scenarios, public beta.

## Status

**Phase 1 complete.** Live integration validated against `data.go.kr` (33/33 pass). Phase 2 swarm work staged behind the Infra Initiative (Observability, Evals, Cost gateway, Safety rails, CI/CD, Secrets — see Issues #462–#468).

## Policy Alignment

KOSMOS's mission directly mirrors **Korea AI Action Plan 2026-2028** (국가인공지능전략위원회, 2026.2.25), Strategic Area 7 (공공AX), Task 58, Principle 9:

> "Open API와 OpenMCP를 제공해 민간에서도 공공서비스를 손쉽게 결합해서 국민들에게 제공할 수 있어야 한다."
> *(Open API and OpenMCP must be provided so that the private sector can easily combine public services and deliver them to citizens.)*

Full citation set: [`docs/presentation.md § 1.5 정책 정합성`](docs/presentation.md#15-정책-정합성--대한민국-ai-행동계획-2026-2028).

## Contributing

Contributions are very welcome — issues, design discussions, tool adapters, and documentation. Start with:

- [CONTRIBUTING.md](CONTRIBUTING.md) — workflow, branch and commit conventions, coding standards
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Contributor Covenant 2.1
- [SECURITY.md](SECURITY.md) — private vulnerability reporting
- [CHANGELOG.md](CHANGELOG.md) — release history

For questions or design proposals, open a [Discussion](https://github.com/umyunsang/KOSMOS/discussions) before writing code on large ideas.

## License

Licensed under the [Apache License 2.0](LICENSE). By contributing, you agree that your contributions will be licensed under the same terms.
