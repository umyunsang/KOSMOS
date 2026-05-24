// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from 'bun:test'

import { InputEvent } from '../../src/ink/events/input-event'
import {
  INITIAL_STATE,
  parseMultipleKeypresses,
  type ParsedKey,
} from '../../src/ink/parse-keypress'
import { splitCoalescedEnter } from '../../src/hooks/useTextInput'

function parseSingleKey(input: string): ParsedKey {
  const [events] = parseMultipleKeypresses(INITIAL_STATE, input)
  const event = events[0]

  if (!event || event.kind !== 'key') {
    throw new Error(`Expected a key event for ${JSON.stringify(input)}`)
  }

  return event
}

describe('Enter key normalization', () => {
  test.each([
    ['CR', '\r'],
    ['LF', '\n'],
    ['CRLF', '\r\n'],
  ])('normalizes %s to Ink key.return', (_label, input) => {
    const event = new InputEvent(parseSingleKey(input))

    expect(event.key.return).toBe(true)
    expect(event.keypress.name).toBe('return')
    expect(event.input).toBe('')
  })

  test('recognizes text followed by LF as one coalesced submit chunk', () => {
    expect(splitCoalescedEnter('/login\n')).toBe('/login')
  })

  test('recognizes text followed by CRLF as one coalesced submit chunk', () => {
    expect(splitCoalescedEnter('/login\r\n')).toBe('/login')
  })

  test('does not treat multiline text paste as coalesced Enter', () => {
    expect(splitCoalescedEnter('line one\nline two\n')).toBeNull()
  })

  test('does not treat backslash LF as coalesced Enter', () => {
    expect(splitCoalescedEnter('line\\\n')).toBeNull()
  })
})
