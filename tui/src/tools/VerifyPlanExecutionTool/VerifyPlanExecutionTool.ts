import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { VERIFY_PLAN_EXECUTION_TOOL_NAME } from './constants.js'

const inputSchema = lazySchema(() => z.object({}).passthrough())
type InputSchema = ReturnType<typeof inputSchema>

export const VerifyPlanExecutionTool = buildTool({
  name: VERIFY_PLAN_EXECUTION_TOOL_NAME,
  searchHint: 'verify a plan execution',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  async description() {
    return 'Verify plan execution'
  },
  async prompt() {
    return 'Verifies internal plan execution.'
  },
  async call() {
    throw new Error('VerifyPlanExecution is not available in this build.')
  },
  renderToolUseMessage() {
    return null
  },
  mapToolResultToToolResultBlockParam(content: string, toolUseID: string) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result' as const,
      content,
    }
  },
} satisfies ToolDef<InputSchema, string>)
