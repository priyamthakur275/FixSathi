import { describe, expect, it } from 'vitest'
import { when } from '../utils/when'

const now = new Date(2026, 10, 25, 18, 0)
describe('when', () => {
  it('names today and yesterday with the time', () => {
    expect(when(new Date(2026, 10, 25, 9, 5).toISOString(), now)).toBe('Today 09:05')
    expect(when(new Date(2026, 10, 24, 23, 59).toISOString(), now)).toBe('Yesterday 23:59')
  })
  it('uses day and month, and the year only when it differs', () => {
    expect(when(new Date(2026, 10, 2, 12).toISOString(), now)).toBe('2 Nov')
    expect(when(new Date(2025, 0, 15, 12).toISOString(), now)).toBe('15 Jan 2025')
  })
  it('returns nothing for a bad date', () => expect(when('nope', now)).toBe(''))
})
