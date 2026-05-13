import { randomUUID } from 'crypto'

import type { ToolResultBlockParam } from 'src/sdk-compat.js'
import type { Progress } from '../Tool.js'
import type { ProgressMessage } from '../types/message.js'
import { CANCEL_MESSAGE } from './permissionMessages.js'

export function createProgressMessage<P extends Progress>({
  toolUseID,
  parentToolUseID,
  data,
}: {
  toolUseID: string
  parentToolUseID: string
  data: P
}): ProgressMessage<P> {
  return {
    type: 'progress',
    data,
    toolUseID,
    parentToolUseID,
    uuid: randomUUID(),
    timestamp: new Date().toISOString(),
  }
}

export function createToolResultStopMessage(
  toolUseID: string,
): ToolResultBlockParam {
  return {
    type: 'tool_result',
    content: CANCEL_MESSAGE,
    is_error: true,
    tool_use_id: toolUseID,
  }
}
