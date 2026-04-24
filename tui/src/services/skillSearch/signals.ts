// [P0 reconstructed · Pass 3 · skillSearch discovery signals]
// Reference: attachments.ts line 88 consumer type + skill_discovery event
//            schema (events have `signal: DiscoverySignal` and
//            `source: 'native' | 'aki' | 'both'`).
//
// DiscoverySignal describes *why* a skill was surfaced to the LLM: a direct
// `@skill` mention, a keyword match against the skill catalog, an auto-
// triggered heuristic ("claude_api_question"), or a user-supplied hint from
// the REPL. Upstream CC ranks and merges these signals when composing the
// skill_discovery context block; KOSMOS keeps them as a typed enum so
// attachments.ts type-checks cleanly.

/**
 * Why a skill appeared in the discovery result. Discriminated union so
 * callers can route on `kind` without parsing prose.
 */
export type DiscoverySignal =
  /** User explicitly referenced a skill via `@skill:<name>`. */
  | { kind: 'explicit_mention'; skillName: string }
  /** Keyword matched the skill catalog's description. */
  | { kind: 'keyword_match'; matchedTerm: string; confidence: number }
  /** Heuristic classifier flagged the prompt (e.g. "claude_api_question"). */
  | { kind: 'classifier'; classifierName: string; score: number }
  /** A prior tool_use output contained a skill cross-reference. */
  | { kind: 'cross_reference'; sourceToolId: string }
  /** No discoverable signal — catalog was surfaced by default heuristic. */
  | { kind: 'default' }

/** Convenience constructors for DiscoverySignal values. */
export const DiscoverySignal = {
  explicit: (skillName: string): DiscoverySignal => ({
    kind: 'explicit_mention',
    skillName,
  }),
  keyword: (matchedTerm: string, confidence: number): DiscoverySignal => ({
    kind: 'keyword_match',
    matchedTerm,
    confidence,
  }),
  classifier: (classifierName: string, score: number): DiscoverySignal => ({
    kind: 'classifier',
    classifierName,
    score,
  }),
  crossRef: (sourceToolId: string): DiscoverySignal => ({
    kind: 'cross_reference',
    sourceToolId,
  }),
  default: (): DiscoverySignal => ({ kind: 'default' }),
} as const
