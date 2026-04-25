// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — AgentVisibilityEntry + shouldActivateSwarm
// (data-model.md §3, FR-025/027).
//
// Five-state proposal-iv visibility surface fed by Spec 027 mailbox events.
// Adding states requires a migration tree ADR.
import { z } from 'zod';

export const AgentState = z.enum([
  'idle',
  'dispatched',
  'running',
  'waiting-permission',
  'done',
]);
export type AgentStateT = z.infer<typeof AgentState>;

export const AgentHealth = z.enum(['green', 'amber', 'red']);
export type AgentHealthT = z.infer<typeof AgentHealth>;

export const AgentVisibilityEntry = z.object({
  agent_id: z.string().min(1),
  ministry: z.string().min(1),
  state: AgentState,
  sla_remaining_ms: z.number().int().nonnegative().nullable(),
  health: AgentHealth,
  rolling_avg_response_ms: z.number().nonnegative().nullable(),
  last_transition_at: z.string().datetime(),
});
export type AgentVisibilityEntryT = z.infer<typeof AgentVisibilityEntry>;

export type ComplexityTag = 'simple' | 'complex';

export type SwarmActivationInput = {
  mentioned_ministries: readonly string[];
  complexity_tag: ComplexityTag;
};

/**
 * FR-027 swarm activation predicate — A+C union semantics from migration
 * tree §UI-D.2: activate when EITHER 3+ explicit ministries are mentioned
 * OR the LLM tags the plan as "complex". Single-condition variants are
 * rejected.
 */
export function shouldActivateSwarm(plan: SwarmActivationInput): boolean {
  const distinct = new Set(plan.mentioned_ministries.map((m) => m.trim()).filter(Boolean));
  return distinct.size >= 3 || plan.complexity_tag === 'complex';
}

// Primitive verb → dot color regulation per docs/wireframes/proposal-iv.mjs
export const PRIMITIVE_DOT_COLOR: Record<string, string> = {
  lookup: 'primitiveLookup',
  submit: 'primitiveSubmit',
  verify: 'primitiveVerify',
  subscribe: 'primitiveSubscribe',
  // plugin.* falls through to primitivePlugin (purple)
};

export function dotColorForPrimitive(verb: string): string {
  if (verb.startsWith('plugin.')) return 'primitivePlugin';
  return PRIMITIVE_DOT_COLOR[verb] ?? 'primitivePlugin';
}
