import type { Report } from '../types'

const OUTCOME: Record<string, string> = { resolved: 'Fixed', not_resolved: 'Not fixed yet', escalated: 'Passed to a senior technician' }

/** A plain-text job summary a technician can send the customer (WhatsApp, SMS) when the visit ends. Only what was recorded
 *  in the session goes in: no AI wording, no confidence figures, nothing the technician did not mark as done. */
export function jobSummary(r: Report): string {
  const d = r.data
  const date = new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  const found = d.diagnosis?.problem_summary
  const done = d.steps_performed.map(s => s.title)
  const outcome = (OUTCOME[d.resolution.outcome] ?? d.resolution.outcome) + (d.resolution.outcome === 'resolved' && d.resolution.first_time_fix ? ' on the first visit' : '')
  const isolated = d.safety.final_state.power_off_confirmed && d.safety.final_state.tester_checked
  return [
    `Service visit: ${d.session.appliance}`,
    `Ref ${r.reference}, ${date}`,
    '',
    d.customer_issue && `Problem: ${d.customer_issue}`,
    found && `Found: ${found}`,
    done.length > 0 && `Work done: ${done.join('; ')}`,
    `Result: ${outcome}`,
    d.resolution.notes && `Notes: ${d.resolution.notes}`,
    isolated && 'Power was switched off and checked with a tester before any work inside.',
    '',
    d.session.technician && `Technician: ${d.session.technician}`,
    'Sent from FixSaathi',
  ].filter((x): x is string => typeof x === 'string').join('\n').replace(/\n{3,}/g, '\n\n').trim()
}

export const whatsappLink = (text: string) => `https://wa.me/?text=${encodeURIComponent(text)}`
