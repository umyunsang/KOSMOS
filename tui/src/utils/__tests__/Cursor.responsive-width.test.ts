import { describe, expect, test } from 'bun:test'

import { Cursor } from '../Cursor.js'

describe('Cursor responsive width', () => {
  test('clamps extremely narrow terminal widths before measuring text', () => {
    const cursor = Cursor.fromText('가나다라마바사', 0, 0)

    expect(cursor.measuredText.columns).toBe(1)
    expect(cursor.measuredText.getWrappedText().length).toBeGreaterThan(0)
  })
})
