// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — AccessibilityPreference entity (data-model.md §5, FR-005).
//
// Persisted at ~/.kosmos/memdir/user/preferences/a11y.json. Owned by Epic #1635.
// Each toggle is independent — combinations like screen_reader + high_contrast
// are valid. SC-011: a toggle change must persist within 500 ms.
import { z } from 'zod';

export const AccessibilityPreference = z.object({
  schema_version: z.literal(1),
  screen_reader: z.boolean().default(false),
  large_font: z.boolean().default(false),
  high_contrast: z.boolean().default(false),
  reduced_motion: z.boolean().default(false),
  updated_at: z.string().datetime(),
});
export type AccessibilityPreferenceT = z.infer<typeof AccessibilityPreference>;

export function freshAccessibilityPreference(): AccessibilityPreferenceT {
  return {
    schema_version: 1,
    screen_reader: false,
    large_font: false,
    high_contrast: false,
    reduced_motion: false,
    updated_at: new Date().toISOString(),
  };
}

export type AccessibilityToggleKey =
  | 'screen_reader'
  | 'large_font'
  | 'high_contrast'
  | 'reduced_motion';

export const ACCESSIBILITY_TOGGLE_KEYS: readonly AccessibilityToggleKey[] = [
  'screen_reader',
  'large_font',
  'high_contrast',
  'reduced_motion',
] as const;
