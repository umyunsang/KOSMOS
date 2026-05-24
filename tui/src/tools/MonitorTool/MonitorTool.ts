import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'

export const MONITOR_TOOL_NAME = 'Monitor'

const inputSchema = lazySchema(() =>
  z.strictObject({
    command: z.string().optional(),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

export const MonitorTool = buildTool({
  name: MONITOR_TOOL_NAME,
  searchHint: 'watch command output in background',
  maxResultSizeChars: 100_000,
  shouldDefer: true,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return false
  },
  isConcurrencySafe() {
    return true
  },
  async description() {
    return 'Run a command in the background and react to output'
  },
  async prompt() {
    return 'Runs a monitor command when the monitor feature is enabled.'
  },
  async call() {
    throw new Error('Monitor is not available in this build.')
  },
  renderToolUseMessage(input) {
    return input.command ?? null
  },
  mapToolResultToToolResultBlockParam(content: string, toolUseID: string) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result' as const,
      content,
    }
  },
} satisfies ToolDef<InputSchema, string>)
