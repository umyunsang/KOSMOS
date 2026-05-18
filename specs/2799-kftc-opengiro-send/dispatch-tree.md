# Dispatch Tree: KFTC OpenGiro Send Adapter

This feature is implemented Lead-solo in the current Codex environment.

Reason: the task set touches credential-sensitive KFTC readiness, one coupled adapter module, schema generation, and count assertions. AGENTS.md prefers Sonnet teammates for 3+ independent tasks, but this session has no Sonnet subagent target available and the write set is tightly coupled.

```text
Phase 1 Setup (T001-T003): Lead solo
Phase 2 Foundational (T004-T007): Lead solo
Phase 3 US1 classification (T008-T010): Lead solo
Phase 4 US2 credential path (T011-T014): Lead solo
Phase 5 US3 send invocation (T015-T019): Lead solo
Phase 6 US4 evidence/schema (T020-T023): Lead solo
Phase 7 validation (T024-T027): Lead solo
```

No worker receives independent write ownership in this run. The implementation still follows the tasks.md ordering and marks tasks complete only after verification.
