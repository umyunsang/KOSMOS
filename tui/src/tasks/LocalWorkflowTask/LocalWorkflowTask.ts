// [P0 reconstructed · Pass 3 · LocalWorkflowTask state]
// Reference: claude-code-from-source Ch3 "Recursive Agent Architecture" +
//            sibling DreamTask.ts + LocalAgentTask.ts (same `TaskStateBase`
//            contract).
//
// `local_workflow` tasks are multi-step scripted routines (slash-command
// backed) that run in the same process. They surface in the background
// tasks indicator via the `BackgroundTaskState` union, and thus must
// carry a status field, isBackgrounded flag, and the generic TaskStateBase
// fields expected by `isBackgroundTask(t)` in `src/tasks/types.ts`.

import type { TaskStateBase } from '../../Task.js'

/** One executed or pending step within a workflow. */
export interface WorkflowStep {
  index: number
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  /** Optional text surfaced to the UI alongside the step. */
  output?: string
  /** Error message if status === 'failed'. */
  error?: string
}

/** State for a single local workflow task. */
export type LocalWorkflowTaskState = TaskStateBase & {
  type: 'local_workflow'
  /** Stable workflow identifier (from the invocation command). */
  workflowId: string
  /** Human-readable title used in the UI. */
  title: string
  /** Whether the user backgrounded this task with Ctrl+B. */
  isBackgrounded: boolean
  /** Ordered list of steps; mutated in place by the executor. */
  steps: WorkflowStep[]
  /** Index of the currently-executing step, -1 if none. */
  currentStepIndex: number
  /** Optional abort controller so kill/ Ctrl+C can interrupt. */
  abortController?: AbortController
}
