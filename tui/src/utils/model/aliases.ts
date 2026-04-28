// KOSMOS Epic #2112: legacy model aliases removed; only the `default` alias survives
// (resolves to K-EXAONE via parseUserSpecifiedModel).
//
// Pre-existing legacy alias names ('opus', 'sonnet', 'haiku', 'best', 'opusplan',
// '*[1m]') are dead under KOSMOS's single-fixed FriendliAI provider invariant.
// Removing them entirely would break callers that still pass these strings (e.g.
// stale settings.json or skill frontmatter) — parseUserSpecifiedModel collapses
// them to K-EXAONE silently, so the union type can be empty here without runtime
// breakage. Kept as `'default'` to retain a non-empty union.
export const MODEL_ALIASES = ['default'] as const

export type ModelAlias = (typeof MODEL_ALIASES)[number]

export function isModelAlias(modelInput: string): modelInput is ModelAlias {
  return MODEL_ALIASES.includes(modelInput as ModelAlias)
}

export const MODEL_FAMILY_ALIASES: readonly string[] = []

export function isModelFamilyAlias(_model: string): boolean {
  return false
}
