// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — UfoMascotPose entity (data-model.md §7, FR-035).
//
// Brand-frozen four-pose UFO mascot in purple palette
// (body #a78bfa, background #4c1d95). Already shipped by Spec 034 token
// catalog; this schema documents the rendering contract.
import { z } from 'zod';

export const UfoMascotPose = z.enum(['idle', 'thinking', 'success', 'error']);
export type UfoMascotPoseT = z.infer<typeof UfoMascotPose>;

export const UFO_PALETTE = {
  body: '#a78bfa',
  background: '#4c1d95',
} as const;

export type UfoPoseContext =
  | { kind: 'repl-empty' }
  | { kind: 'llm-streaming' }
  | { kind: 'tool-running' }
  | { kind: 'awaiting-permission' }
  | { kind: 'final-answer' }
  | { kind: 'permission-granted' }
  | { kind: 'permission-denied' }
  | { kind: 'error-shown' };

export function poseForContext(ctx: UfoPoseContext): UfoMascotPoseT {
  switch (ctx.kind) {
    case 'repl-empty':
      return 'idle';
    case 'llm-streaming':
    case 'tool-running':
    case 'awaiting-permission':
      return 'thinking';
    case 'final-answer':
    case 'permission-granted':
      return 'success';
    case 'permission-denied':
    case 'error-shown':
      return 'error';
  }
}
