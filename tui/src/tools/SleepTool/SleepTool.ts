import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { sleep } from '../../utils/sleep.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { DESCRIPTION, SLEEP_TOOL_NAME, SLEEP_TOOL_PROMPT } from './prompt.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    duration_ms: z.number().int().min(0).max(300_000).default(60_000),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

export const SleepTool = buildTool({
  name: SLEEP_TOOL_NAME,
  searchHint: 'wait without running shell sleep',
  maxResultSizeChars: 1_000,
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return true
  },
  interruptBehavior() {
    return 'cancel'
  },
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return SLEEP_TOOL_PROMPT
  },
  async call(input, context) {
    await sleep(input.duration_ms, context.abortController.signal)
    return { data: `Slept for ${input.duration_ms} ms.` }
  },
  renderToolUseMessage(input) {
    return `sleep ${input.duration_ms ?? 60_000} ms`
  },
  mapToolResultToToolResultBlockParam(content: string, toolUseID: string) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result' as const,
      content,
    }
  },
} satisfies ToolDef<InputSchema, string>)
