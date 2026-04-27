# Caller classification — Epic #2112 / FR-006 caller-reach rule

## Bucket A — inside SC-1 perimeter (`tui/src/utils/model/`)
  → direct rewrite allowed; helper exports may be removed

tui/src/utils/model/agent.ts
tui/src/utils/model/model.ts
tui/src/utils/model/modelOptions.ts

## Bucket B — outside SC-1 perimeter (P2 boundary)
  → MUST keep helper as thin K-EXAONE alias; annotate `[Deferred to P2 — issue #2147]`

tui/src/commands/insights.ts
tui/src/components/messages/AssistantTextMessage.tsx
tui/src/memdir/findRelevantMemories.ts
tui/src/services/api/claude.ts
tui/src/services/tokenEstimation.ts
tui/src/utils/attachments.ts

## Conclusion
Bucket B has ≥1 caller → FR-006 rule resolves to ALIAS-PRESERVATION.
T010 MUST keep getDefault{Sonnet,Opus,Haiku}Model as thin aliases returning getDefaultMainLoopModel().
T009 MUST keep firstPartyNameToCanonical exported (collapsed to fail-safe single branch).
