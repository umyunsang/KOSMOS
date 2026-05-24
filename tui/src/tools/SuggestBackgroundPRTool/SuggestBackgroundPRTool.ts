import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'

export const SUGGEST_BACKGROUND_PR_TOOL_NAME = 'SuggestBackgroundPR'

const inputSchema = lazySchema(() => z.object({}).passthrough())
type InputSchema = ReturnType<typeof inputSchema>

export const SuggestBackgroundPRTool = buildTool({
  name: SUGGEST_BACKGROUND_PR_TOOL_NAME,
  searchHint: 'suggest background pull request work',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  async description() {
    return 'Suggest background PR work'
  },
  async prompt() {
    return 'Suggests background pull request work in internal builds.'
  },
  async call() {
    throw new Error('SuggestBackgroundPR is not available in this build.')
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
