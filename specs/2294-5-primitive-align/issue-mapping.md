# Issue Mapping — Epic γ #2294

**Created**: 2026-04-29 | **Total sub-issues linked**: 29 (27 tasks + 2 deferred)
**Verification**: `gh api graphql ... issue(number: 2294) { subIssues { totalCount } }` → `29`

## Task → Issue mapping (27)

| Task | Issue | Phase | Story | Owner |
|---|---|---|---|---|
| T001 | [#2365](https://github.com/umyunsang/KOSMOS/issues/2365) | 1 Setup | — | Lead solo |
| T002 | [#2366](https://github.com/umyunsang/KOSMOS/issues/2366) | 1 Setup | — | Lead solo |
| T003 | [#2367](https://github.com/umyunsang/KOSMOS/issues/2367) | 2 Foundational | — | Lead solo |
| T004 | [#2368](https://github.com/umyunsang/KOSMOS/issues/2368) | 2 Foundational | — | Lead solo |
| T005 | [#2369](https://github.com/umyunsang/KOSMOS/issues/2369) | 2 Foundational | — | Lead solo |
| T006 | [#2370](https://github.com/umyunsang/KOSMOS/issues/2370) | 3 | US1 | sonnet-lookup |
| T007 | [#2371](https://github.com/umyunsang/KOSMOS/issues/2371) | 3 | US1 | sonnet-lookup |
| T008 | [#2372](https://github.com/umyunsang/KOSMOS/issues/2372) | 3 | US1 | sonnet-lookup |
| T009 | [#2373](https://github.com/umyunsang/KOSMOS/issues/2373) | 3 | US1 | sonnet-lookup |
| T010 | [#2374](https://github.com/umyunsang/KOSMOS/issues/2374) | 4 | US2 | sonnet-submit `[P]` |
| T011 | [#2375](https://github.com/umyunsang/KOSMOS/issues/2375) | 4 | US2 | sonnet-submit `[P]` |
| T012 | [#2376](https://github.com/umyunsang/KOSMOS/issues/2376) | 4 | US2 | sonnet-submit `[P]` |
| T013 | [#2377](https://github.com/umyunsang/KOSMOS/issues/2377) | 4 | US2 | sonnet-verify `[P]` |
| T014 | [#2378](https://github.com/umyunsang/KOSMOS/issues/2378) | 4 | US2 | sonnet-verify `[P]` |
| T015 | [#2379](https://github.com/umyunsang/KOSMOS/issues/2379) | 4 | US2 | sonnet-verify `[P]` |
| T016 | [#2380](https://github.com/umyunsang/KOSMOS/issues/2380) | 4 | US2 | sonnet-subscribe `[P]` |
| T017 | [#2381](https://github.com/umyunsang/KOSMOS/issues/2381) | 4 | US2 | sonnet-subscribe `[P]` |
| T018 | [#2382](https://github.com/umyunsang/KOSMOS/issues/2382) | 4 | US2 | sonnet-subscribe `[P]` |
| T019 | [#2383](https://github.com/umyunsang/KOSMOS/issues/2383) | 4 | US2 | sonnet-bootguard |
| T020 | [#2384](https://github.com/umyunsang/KOSMOS/issues/2384) | 4 | US2 | sonnet-bootguard |
| T021 | [#2385](https://github.com/umyunsang/KOSMOS/issues/2385) | 5 | US3 | sonnet-citation |
| T022 | [#2386](https://github.com/umyunsang/KOSMOS/issues/2386) | 6 | US4 | sonnet-regress `[P]` |
| T023 | [#2387](https://github.com/umyunsang/KOSMOS/issues/2387) | 6 | US4 | sonnet-regress `[P]` |
| T024 | [#2388](https://github.com/umyunsang/KOSMOS/issues/2388) | 7 | US1 | Lead solo (PTY) |
| T025 | [#2389](https://github.com/umyunsang/KOSMOS/issues/2389) | 8 Polish | — | Lead solo `[P]` |
| T026 | [#2390](https://github.com/umyunsang/KOSMOS/issues/2390) | 8 Polish | — | Lead solo `[P]` |
| T027 | [#2391](https://github.com/umyunsang/KOSMOS/issues/2391) | 8 Polish | — | Lead solo |

## Deferred placeholders (2)

| Issue | Item | Target |
|---|---|---|
| [#2392](https://github.com/umyunsang/KOSMOS/issues/2392) | MCP-side primitive permission-UI downgrade pattern | Phase 5 plugin DX follow-up |
| [#2393](https://github.com/umyunsang/KOSMOS/issues/2393) | `prompts/system_v1.md` 5-primitive citizen-friendly tone update | Phase ζ (optional) |

## Pre-existing deferred (linked elsewhere — referenced from spec.md)

| Issue | Item | Origin |
|---|---|---|
| [#2296](https://github.com/umyunsang/KOSMOS/issues/2296) | 9 new Mock adapters (Singapore APEX style) + DelegationToken | Epic ε |
| [#2297](https://github.com/umyunsang/KOSMOS/issues/2297) | E2E PTY scenario + policy-mapping doc + 5 OPAQUE scenarios | Epic ζ |
| [#2362](https://github.com/umyunsang/KOSMOS/issues/2362) | Adapter `real_classification_url` real-policy verification | Epic δ deferred |

## Sub-Issues API v2 verification

```bash
gh api graphql -f query='query { repository(owner: "umyunsang", name: "KOSMOS") { issue(number: 2294) { subIssues { totalCount } } } }'
# → totalCount: 29
```

## Notes

- Title pattern: `TXXX: <short-action>`. The detailed acceptance signal lives in `tasks.md` and the contract docs — issue body links back to them.
- Labels applied: `size/S` or `size/M`; `agent-ready` + `parallel-safe` on `[P]` tasks; `needs-spec` + `deferred` on placeholders.
- The `task` label was not used — repo precedent (`#2360` etc.) shows existing task issues run unlabelled there. Memory `feedback_subissue_100_cap` cap stays at 29/100 well below the 90 budget.
- PR `Closes` line (per `feedback_pr_closing_refs`): only `Closes #2294` — Task sub-issues stay open until merge then close automatically via Epic closure rule.
