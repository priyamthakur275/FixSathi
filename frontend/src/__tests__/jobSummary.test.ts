import { describe, expect, it } from 'vitest'
import { jobSummary, whatsappLink } from '../utils/jobSummary'
import type { Report } from '../types'

const report = (over: Partial<Report['data']> = {}): Report => ({
  id: 'r1', reference: 'R-9FF43A', session_id: 's1', session_reference: 'FS-1', appliance: 'Ceiling fan', appliance_type: 'ceiling_fan', technician: 'Ravi Kumar',
  resolution_status: 'resolved', created_at: '2026-11-25T05:00:00Z', title: 'Fan',
  data: {
    session: { reference: 'FS-1', appliance: 'Ceiling fan', title: 'Fan', started_at: '', technician: 'Ravi Kumar' },
    customer_issue: 'Fan hums and runs slow', diagnosis: { problem_summary: 'Weak capacitor', faults: [], model_identifier: 'x', note: '' },
    steps_performed: [{ step_number: 1, title: 'Replaced the capacitor', completed_at: null }], steps_not_performed: [], parts_identified: [],
    safety: { final_state: { power_off_confirmed: true, tester_checked: true, expired: false }, confirmation_events: [], blocked_attempts: 0, disclaimer: '' },
    escalations: [], resolution: { outcome: 'resolved', first_time_fix: true, notes: null }, feedback: null, ...over,
  },
})

describe('customer job summary', () => {
  it('says what was found, done and the result, in plain words', () => {
    const t = jobSummary(report())
    expect(t).toContain('Service visit: Ceiling fan')
    expect(t).toContain('Problem: Fan hums and runs slow')
    expect(t).toContain('Found: Weak capacitor')
    expect(t).toContain('Work done: Replaced the capacitor')
    expect(t).toContain('Result: Fixed on the first visit')
    expect(t).toContain('checked with a tester')
    expect(t).not.toMatch(/%|AI|confidence/)
  })
  it('leaves out what was not recorded', () => {
    const t = jobSummary(report({ diagnosis: null, steps_performed: [], safety: { final_state: { power_off_confirmed: true, tester_checked: false, expired: false }, confirmation_events: [], blocked_attempts: 0, disclaimer: '' } }))
    expect(t).not.toContain('Found:')
    expect(t).not.toContain('Work done:')
    expect(t).not.toContain('tester')
    expect(t).not.toMatch(/\n{3,}/)
  })
  it('makes a WhatsApp link with the text encoded', () => {
    expect(whatsappLink('a b\nc')).toBe('https://wa.me/?text=a%20b%0Ac')
  })
})
