import { describe, expect, it } from 'bun:test'
import {
  INITIAL_STATE,
  parseMultipleKeypresses,
  type ParsedKey,
} from '../../src/ink/parse-keypress'
import { InputEvent } from '../../src/ink/events/input-event'

function parseSingleKey(input: string): ParsedKey {
  const [events] = parseMultipleKeypresses(INITIAL_STATE, input)
  const event = events[0]

  if (!event || event.kind !== 'key') {
    throw new Error(`Expected a key event for ${JSON.stringify(input)}`)
  }

  return event
}

describe('Enter normalization', () => {
  it('normalizes carriage return to Ink key.return', () => {
    const event = new InputEvent(parseSingleKey('\r'))

    expect(event.key.return).toBe(true)
    expect(event.keypress.name).toBe('return')
    expect(event.input).toBe('')
  })

  it('normalizes line feed to Ink key.return', () => {
    const event = new InputEvent(parseSingleKey('\n'))

    expect(event.key.return).toBe(true)
    expect(event.keypress.name).toBe('return')
    expect(event.input).toBe('')
  })

  it('normalizes CRLF to Ink key.return', () => {
    const event = new InputEvent(parseSingleKey('\r\n'))

    expect(event.key.return).toBe(true)
    expect(event.keypress.name).toBe('return')
    expect(event.input).toBe('')
  })
})
