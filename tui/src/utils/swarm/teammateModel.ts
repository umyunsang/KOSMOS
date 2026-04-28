// KOSMOS Epic #2112: legacy CLAUDE_OPUS_4_6_CONFIG removed; teammate fallback
// resolves to the canonical K-EXAONE model via getDefaultMainLoopModel().
import { getDefaultMainLoopModel } from '../model/model.js'

export function getHardcodedTeammateModelFallback(): string {
  return getDefaultMainLoopModel()
}
