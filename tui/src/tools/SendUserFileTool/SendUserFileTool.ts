import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { SEND_USER_FILE_TOOL_NAME } from './prompt.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    files: z.array(z.string()).default([]),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

export const SendUserFileTool = buildTool({
  name: SEND_USER_FILE_TOOL_NAME,
  searchHint: 'send files to the user',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  async description() {
    return 'Send files to the user'
  },
  async prompt() {
    return 'Sends files to the user when assistant-mode file sending is enabled.'
  },
  async call() {
    throw new Error('SendUserFile is not available in this build.')
  },
  renderToolUseMessage(input) {
    return input.files.length > 0 ? input.files.join(', ') : null
  },
  mapToolResultToToolResultBlockParam(content: string, toolUseID: string) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result' as const,
      content,
    }
  },
} satisfies ToolDef<InputSchema, string>)
