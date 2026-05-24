import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'

export const TUNGSTEN_TOOL_NAME = 'Tungsten'

const inputSchema = lazySchema(() => z.object({}).passthrough())
type InputSchema = ReturnType<typeof inputSchema>

export function clearSessionsWithTungstenUsage(): void {}

export function resetInitializationState(): void {}

export const TungstenTool = buildTool({
  name: TUNGSTEN_TOOL_NAME,
  searchHint: 'run commands in a virtual terminal',
  maxResultSizeChars: 100_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isEnabled() {
    return process.env.USER_TYPE === 'ant'
  },
  isConcurrencySafe() {
    return false
  },
  isReadOnly() {
    return false
  },
  async description() {
    return 'Run commands in a virtual terminal'
  },
  async prompt() {
    return 'Runs an internal virtual-terminal workflow. This tool is only available in Anthropic internal builds.'
  },
  async call() {
    throw new Error('Tungsten is not available in this build.')
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
