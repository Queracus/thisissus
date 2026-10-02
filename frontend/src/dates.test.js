import { describe, expect, it } from 'vitest'
import { formatWhen, fromLocalInput, toLocalInput } from './dates.js'

describe('date helpers', () => {
  it('round-trips datetime-local values through ISO', () => {
    expect(toLocalInput(fromLocalInput('2026-06-14T12:30'))).toBe('2026-06-14T12:30')
    expect(fromLocalInput('')).toBeNull()
  })

  it('formats a multi-day trip as a range', () => {
    const range = formatWhen('en', '2026-06-14T10:00:00Z', '2026-06-16T10:00:00Z')
    expect(range).toMatch(/14/)
    expect(range).toMatch(/16/)
  })
})
