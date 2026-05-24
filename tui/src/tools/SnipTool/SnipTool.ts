import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { SNIP_TOOL_NAME } from './prompt.js'

const inputSchema = lazySchema(() => z.object({}).passthrough())
type InputSchema = ReturnType<typeof inputSchema>

export const SnipTool = buildTool({
  name: SNIP_TOOL_NAME,
  searchHint: 'snip large transcript output',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  async description() {
    return 'Snip large transcript output'
  },
  async prompt() {
    return 'Snips large transcript output when history snip is enabled.'
  },
  async call() {
    throw new Error('Snip is not available in this build.')
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
