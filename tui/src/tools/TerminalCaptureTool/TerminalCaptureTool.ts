import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { TERMINAL_CAPTURE_TOOL_NAME } from './prompt.js'

const inputSchema = lazySchema(() => z.object({}).passthrough())
type InputSchema = ReturnType<typeof inputSchema>

export const TerminalCaptureTool = buildTool({
  name: TERMINAL_CAPTURE_TOOL_NAME,
  searchHint: 'capture terminal panel output',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  async description() {
    return 'Capture terminal panel output'
  },
  async prompt() {
    return 'Captures terminal panel output when the terminal panel feature is enabled.'
  },
  async call() {
    throw new Error('Terminal capture is not available in this build.')
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
