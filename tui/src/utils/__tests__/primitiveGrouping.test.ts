import { describe, expect, test } from 'bun:test'
import { LookupPrimitive } from '../../tools/LookupPrimitive/LookupPrimitive.js'
import { applyGrouping } from '../groupToolUses.js'

describe('applyGrouping — primitive tool calls', () => {
  test('does not group repeated find calls from the same assistant response', () => {
    const messages = [
      {
        type: 'assistant',
        uuid: 'assistant-find-1',
        message: {
          id: 'assistant-turn-1',
          content: [
            {
              type: 'tool_use',
              id: 'toolu_find_1',
              name: 'find',
              input: { tool_id: 'kma_current_observation', params: {} },
            },
          ],
        },
      },
      {
        type: 'assistant',
        uuid: 'assistant-find-2',
        message: {
          id: 'assistant-turn-1',
          content: [
            {
              type: 'tool_use',
              id: 'toolu_find_2',
              name: 'find',
              input: { tool_id: 'kma_forecast_fetch', params: {} },
            },
          ],
        },
      },
    ]

    const result = applyGrouping(
      messages as Parameters<typeof applyGrouping>[0],
      [LookupPrimitive],
      false,
    )

    expect(result.messages).toHaveLength(2)
    expect(result.messages[0]?.type).toBe('assistant')
    expect(result.messages[1]?.type).toBe('assistant')
  })
})
