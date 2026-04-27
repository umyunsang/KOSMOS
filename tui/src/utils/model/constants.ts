// KOSMOS Epic #2112: single source-of-truth for the canonical K-EXAONE model id
// inside the TUI utils/model/ subtree. Imported by model.ts, configs.ts,
// modelAllowlist.ts, validateModel.ts to satisfy FR-012 without re-introducing
// module-init cycles.
//
// FR-012 declared anchor (other allowed prod sites are pre-existing, tracked
// for P2 cleanup):
//   - tui/src/utils/model/constants.ts (this file)
//   - src/kosmos/llm/config.py:37 (Python source-of-truth)
//   - tui/src/ipc/llmClient.ts:31 (Spec 1633 query engine, P2 cleanup)
//   - tui/src/tools/TranslateTool/TranslateTool.ts:64 (Spec 022, P2 cleanup)

export const KOSMOS_K_EXAONE_MODEL = 'LGAI-EXAONE/K-EXAONE-236B-A23B'
export const KOSMOS_K_EXAONE_SHORT = 'k-exaone'
export const KOSMOS_K_EXAONE_DISPLAY = 'K-EXAONE'
