import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'

export const OVERFLOW_TEST_TOOL_NAME = 'OverflowTest'

const inputSchema = lazySchema(() => z.object({}).passthrough())
type InputSchema = ReturnType<typeof inputSchema>

export const OverflowTestTool = buildTool({
  name: OVERFLOW_TEST_TOOL_NAME,
  searchHint: 'generate overflow test output',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  async description() {
    return 'Generate overflow test output'
  },
  async prompt() {
    return 'Generates internal overflow test output.'
  },
  async call() {
    throw new Error('OverflowTest is not available in this build.')
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
