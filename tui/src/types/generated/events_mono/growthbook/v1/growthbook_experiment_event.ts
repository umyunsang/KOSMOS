// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — protobuf events_mono stub (GrowthBook variant).
// See `claude_code_internal_event.ts` sibling for rationale.

export class GrowthbookExperimentEvent {
  static fromJSON(_object: unknown): GrowthbookExperimentEvent {
    return new GrowthbookExperimentEvent()
  }
  static encode(_message: GrowthbookExperimentEvent): { finish(): Uint8Array } {
    return { finish: () => new Uint8Array(0) }
  }
  toJSON(): unknown {
    return {}
  }
}
