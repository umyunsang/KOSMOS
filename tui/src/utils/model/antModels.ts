// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Anthropic model alias resolution is replaced by the K-EXAONE single
// constant in `utils/model/model.ts::getDefaultMainLoopModel()`. Callers that
// still reach for `resolveAntModel()` get the K-EXAONE ID back.

const KOSMOS_MODEL = 'LGAI-EXAONE/K-EXAONE-236B-A23B'

export function resolveAntModel(_alias: string): string {
  return KOSMOS_MODEL
}
