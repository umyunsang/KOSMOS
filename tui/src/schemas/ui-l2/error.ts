// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — ErrorEnvelope entity (data-model.md §6, FR-012).
//
// Three differentiated styles per migration tree §UI-B.4:
// - llm     → purple accent + brain glyph
// - tool    → orange accent + wrench glyph
// - network → red accent + signal-broken glyph
import { z } from 'zod';

export const ErrorEnvelopeType = z.enum(['llm', 'tool', 'network']);
export type ErrorEnvelopeTypeT = z.infer<typeof ErrorEnvelopeType>;

export const ErrorEnvelope = z.object({
  type: ErrorEnvelopeType,
  title_ko: z.string().min(1),
  title_en: z.string().min(1),
  detail_ko: z.string().nullable(),
  detail_en: z.string().nullable(),
  retry_suggested: z.boolean(),
  occurred_at: z.string().datetime(),
});
export type ErrorEnvelopeT = z.infer<typeof ErrorEnvelope>;

export type ErrorVisualSpec = {
  glyph: string;
  colorToken: string;
};

export const ERROR_VISUAL: Record<ErrorEnvelopeTypeT, ErrorVisualSpec> = {
  llm: { glyph: '🧠', colorToken: 'errorLlm' },
  tool: { glyph: '🔧', colorToken: 'errorTool' },
  network: { glyph: '📡', colorToken: 'errorNetwork' },
};
