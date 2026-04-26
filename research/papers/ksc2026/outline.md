# KSC 2026 Paper Outline

## Title

**KOSMOS: A Conversational Agent Platform for Cross-Ministry Public Service Orchestration via LLM Tool Calling**

KOSMOS: LLM 도구 호출 기반 범부처 공공서비스 대화형 오케스트레이션 플랫폼

## Authors

- Um Yunsang (Affiliation TBD)
- Advisor (TBD)

## Abstract structure

1. Problem: 5,000+ fragmented government APIs, citizens cannot navigate
2. Approach: Six-layer conversational agent platform with domain-specific adaptations
3. Key contributions: bilingual tool discovery, bypass-immune permission pipeline
4. Results: (TBD after experiments)
5. Conclusion: (TBD)

## Paper structure (6-8 pages, KSC format)

### 1. Introduction (1 page)
- Problem statement: fragmented government digital services
- Motivation: LLM agents as unifying interface
- Contribution claims:
  - C1: Schema-driven tool discovery over 5,000+ heterogeneous government APIs
  - C2: Bypass-immune permission pipeline for citizen PII protection
  - C3: Multi-ministry agent coordination with legal dependency ordering
- Paper organization

### 2. Related Work (1 page)
- LLM agent frameworks (ReAct, tool-use agents, multi-agent systems)
- Government digital services and API orchestration
- Conversational AI for public services
- Position KOSMOS: domain-specific agent platform, not general framework

### 3. System Architecture (2 pages)
- Six-layer overview (architecture diagram in figures/)
- Layer 1: Query Engine — async generator tool loop
- Layer 2: Tool System — schema-driven registry, lazy discovery, cache partitioning
- Layer 3: Permission Pipeline — 7-step gauntlet, bypass-immune checks
- Layer 4: Agent Swarms — coordinator-worker, mailbox IPC
- Layer 5: Context Assembly — multi-tier context, compression pipeline
- Layer 6: Error Recovery — retry matrix for government API failure modes

### 4. Implementation (1 page)
- Stack: Python 3.12+, EXAONE via FriendliAI, Pydantic v2
- API adapters: N adapters covering M ministries
- Clean-room design methodology and reference sources

### 5. Evaluation (1.5 pages)
- E1: Task completion rate (50 scenarios, 5+ ministries)
- E2: Tool discovery precision/recall
- E3: Cost analysis (cache hit rate, token usage)
- E4: User study results (SUS score, completion time)
- E5: Ablation study (layer removal impact)

### 6. Discussion (0.5 page)
- Limitations: API coverage, LLM hallucination risk, evaluation scale
- Generalizability to other countries' government API ecosystems

### 7. Conclusion (0.5 page)
- Summary of contributions
- Future work: Phase 2 (swarm), Phase 3 (production)

## Key figures needed

- Fig 1: Six-layer architecture diagram
- Fig 2: Query engine tool loop flow
- Fig 3: Permission pipeline gauntlet steps
- Fig 4: Tool discovery accuracy (precision/recall chart)
- Fig 5: Task completion rate comparison (bar chart)
- Fig 6: User study SUS scores (box plot)

## References to include

- Anthropic (2025). Claude Agent SDK. MIT License.
- OpenAI (2025). OpenAI Agents SDK. MIT License.
- Yao et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models.
- Schick et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools.
- Wu et al. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation.
- Korea MOIS. data.go.kr public data portal statistics.
- EXAONE / LG AI Research references.
