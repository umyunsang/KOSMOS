// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · LookupPrimitive prompt strings.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 2

export const LOOKUP_TOOL_NAME = 'lookup'

/** One-line bilingual description shown to the LLM. */
export const DESCRIPTION =
  'Discover and invoke Korean public-service adapters. 한국 공공 API 어댑터 검색 및 호출.'

/** Extended prompt included in the system-prompt tool-use section. */
export const LOOKUP_TOOL_PROMPT = `Discover and invoke Korean public-service adapters registered in the KOSMOS tool registry.

Two modes:

**mode=search** — BM25+dense hybrid search over registered adapters.
  Input: { mode: "search", query: string, primitive_filter?: "lookup"|"submit"|"verify"|"subscribe"|null, top_k?: number }
  Output: { mode: "search", results: Array<{ tool_id, primitive, ministry, score, search_hint }> }
  Use this first to find which adapter serves the citizen's need.

**mode=fetch** — Direct adapter invocation by tool_id.
  Input: { mode: "fetch", tool_id: string, params: object }
  Output: { mode: "fetch", tool_id: string, result: object }
  Use this after a search result identifies the correct adapter.

Rules:
- Always run mode=search before mode=fetch when the adapter is unknown.
- Do NOT carry params or tool_id in mode=search requests.
- Respect the primitive_filter to restrict results to a specific primitive type.
- top_k defaults to 5; increase only when the user asks for more options.
- Korean and English queries both work; prefer the citizen's natural language.`
