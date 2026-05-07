---
name: kosmos-reference-first
description: Use before any KOSMOS code, prompt, TUI, tool-loop, adapter, workflow, debugging, or verification work. Forces the Claude Code restored source, KOSMOS canonical docs, adapter docs, and primary-source research to be read and cited before implementation.
---

# KOSMOS Reference First

Use this skill before planning or editing KOSMOS runtime behavior. Its job is to prevent memory-only design and keep every change anchored to the KOSMOS thesis:

`KOSMOS = Claude Code original harness + K-EXAONE/FriendliAI + Korean public-service tool surface`.

## Bootstrap Gate

Do not edit code until these sources are checked for the task:

1. Read `docs/onboarding/codex-continuation.md`.
2. Read the task-relevant parts of `docs/vision.md` and `docs/requirements/kosmos-migration-tree.md`.
3. Find the matching Claude Code restored-source path under `.references/claude-code-sourcemap/restored-src/`. Never modify files under `.references/`.
4. Read local adapter/API docs under `docs/api/`, `specs/`, and local downloaded agency documents when the task touches a public-service tool.
5. If the task asks for latest/deep research or the primary source is not already cataloged, use current primary sources: official agency docs, official framework docs, upstream repositories, standards, or vendor docs. Avoid blogs and summaries unless they are only leads to primary sources.

## Evidence Note

Before patching, produce a short reference bootstrap note in the conversation or task artifact:

```text
Reference bootstrap:
- KOSMOS thesis/docs:
- CC restored-src files:
- Adapter/API sources:
- External primary sources:
- Implementation constraints:
- Unknowns or blocked evidence:
```

If any required evidence is missing, stop implementation and gather it. Do not fill the gap from model memory.

For public-service adapter bugs, implementation is blocked until the evidence note includes sanitized artefacts proving:

- The credential exists and the upstream accepts or rejects it explicitly.
- The endpoint URL is the one documented by the agency source.
- The request parameter names, required/optional fields, and encoded values match the agency source.
- The live response header, result code, total count, and item shape are captured without secrets.
- A zero-result response was reproduced with valid credential, endpoint, and parameters before any alternate path is proposed.
- Live public API contract checks must be direct `curl` probes first. Helper scripts are not primary evidence for endpoint/key/parameter validation.

## Search Patterns

Use `rg` first:

```bash
rg -n "runTools|tool_result|is_error|validateInput|PermissionRequest|useKeybinding|CtrlO|toggleTranscript" .references/claude-code-sourcemap/restored-src/src
rg -n "Primitive|GovAPITool|ToolRegistry|lookup|resolve_location|submit|verify|subscribe" src docs specs
rg -n "<adapter_id>|<agency>|<endpoint>|<schema field>" docs/api specs ~/Downloads
```

Replace placeholders with the adapter, agency, endpoint, scenario, or UI action under investigation.

## Implementation Rules

- Keep the Claude Code harness behavior byte-parity by default. KOSMOS-specific behavior must be one of the two sanctioned swaps or a documented public-service constraint.
- Prefer CC reference behavior, adapter metadata, registry search, official schemas, recorded fixtures, and cited agency policy over keyword routing or static service tables.
- A recoverable tool or schema failure must remain inside the agentic loop unless the CC reference proves it is terminal.
- TUI-visible error, permission, transcript, and expand/collapse behavior must be checked against the CC components before changing KOSMOS render code.
- For live public APIs, confirm the official endpoint, request parameters, response shape, credential name, and CI exclusion policy before claiming correctness.
- Do not add fallback routing, static recovery tables, hardcoded alternate endpoints, or "make it work" branches for an adapter before the live evidence gate above is complete and cited in the implementation artifact.
- Any fallback must name the root cause, log its failure mode, and be removed with the root-cause fix.

## Exit Criteria

Proceed to edits only when the evidence note identifies the relevant CC files and KOSMOS/API sources, and the intended change is traceable to those sources.
