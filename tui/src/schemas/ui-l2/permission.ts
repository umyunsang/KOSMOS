// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — PermissionReceipt entity (data-model.md §2, FR-018).
//
// Citizen-side projection of the Spec 033 permission ledger. The TUI never
// writes the ledger directly — writes go through IPC to the Python service.
// This schema is the read model the surface displays.
import { z } from 'zod';

export const PermissionLayer = z.union([
  z.literal(1),
  z.literal(2),
  z.literal(3),
]);
export type PermissionLayerT = z.infer<typeof PermissionLayer>;

export const PermissionDecision = z.enum([
  'allow_once',
  'allow_session',
  'deny',
  'auto_denied_at_cancel',
  'timeout_denied',
]);
export type PermissionDecisionT = z.infer<typeof PermissionDecision>;

export const PermissionReceipt = z.object({
  receipt_id: z.string().regex(/^rcpt-[A-Za-z0-9_-]{8,}$/),
  layer: PermissionLayer,
  tool_name: z.string().min(1),
  decision: PermissionDecision,
  decided_at: z.string().datetime(),
  session_id: z.string().min(1),
  revoked_at: z.string().datetime().nullable(),
});
export type PermissionReceiptT = z.infer<typeof PermissionReceipt>;

export type LayerVisualSpec = {
  glyph: string;
  colorToken: string;
  ariaLabel: string;
};

// FR-016: green ⓵ / orange ⓶ / red ⓷
export const LAYER_VISUAL: Record<PermissionLayerT, LayerVisualSpec> = {
  1: { glyph: '⓵', colorToken: 'permLayer1', ariaLabel: 'Layer 1 (low risk)' },
  2: { glyph: '⓶', colorToken: 'permLayer2', ariaLabel: 'Layer 2 (medium risk)' },
  3: { glyph: '⓷', colorToken: 'permLayer3', ariaLabel: 'Layer 3 (high risk)' },
};

export function isReceiptRevoked(r: PermissionReceiptT): boolean {
  return r.revoked_at !== null;
}
