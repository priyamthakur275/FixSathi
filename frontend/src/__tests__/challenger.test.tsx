import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { AppProvider } from '../context/AppContext'
import { PrefsProvider } from '../context/PrefsContext'
import RepairSessionPage from '../pages/RepairSessionPage'
import EvaluationPage from '../pages/EvaluationPage'
import * as services from '../services'
import type { Diagnosis, RepairSession, RepairStep, SafetyState } from '../types'

const wrap = (ui: ReactNode, path = '/session/s1') => render(
  <AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={[path]}><Routes><Route path="/session/:id" element={ui} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>,
)

function signedIn() {
  localStorage.setItem('fixsaathi.refresh', 'saved-refresh-token')
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ access_token: 'a', refresh_token: 'r2', expires_in: 900 }), { status: 200, headers: { 'content-type': 'application/json' } })))
  vi.spyOn(services.authService, 'currentUser').mockResolvedValue({
    id: 'u1', full_name: 'Ravi Tech', email: 'ravi@example.com', role: 'technician',
    preferred_language: 'English', organisation_id: null, organisation_name: null, created_at: '2026-11-28T00:00:00Z',
  } as never)
}

const session: RepairSession = {
  id: 's1', reference: 'REF-1', title: 'Split AC not cooling', appliance_type: 'split_ac', appliance_label: 'Split AC',
  issue_description: 'CH38 on indoor display', status: 'active', technician_id: 'u1', technician_name: 'Ravi Tech',
  first_time_fix: null, started_at: '2026-11-28T00:00:00Z', completed_at: null, report_id: null, nameplate: null,
}

const diagDisagree: Diagnosis = {
  id: 'd1', problem_summary: 'Possible low refrigerant or wiring fault',
  faults: [{ fault: 'Low refrigerant (CH38)', explanation: 'Pressure drop', confidence: 0.78, evidence: [], status: 'supported_by_records', record_ids: ['mfr:lg-ac-ch38'] }],
  recommended_checks: ['Check indoor filter'], follow_up_questions: [], safety_requirements: ['Switch off MCB first'],
  requires_escalation: false, model_identifier: 'gemini-3.5-flash-lite', latency_ms: 1200,
  created_at: '2026-11-28T00:00:00Z', confidence_note: 'AI estimate', confirmed_findings: [],
  missing_information: [], required_tools: [], knowledge_coverage: 'grounded',
  sources: [{ record_id: 'mfr:lg-ac-ch38', source_name: 'LG Guide', source_url: null, license: 'ref', verification_status: 'verified_source', match: 'error_code', related_category: true }],
  challenger: {
    status: 'ok', agrees: false, confidence_before: 0.78, revised_confidence: 0.52,
    objections: [{
      claim: 'Could be a loose flare nut rather than compressor fault.',
      claim_hi: 'यह कम्प्रेशर की जगह फ्लेयर नट लीक भी हो सकता है।',
      why: 'Recent installation was not ruled out.',
      why_hi: 'नई इंस्टॉलेशन की जाँच अभी नहीं हुई है।',
      evidence_id: 'mfr:lg-ac-ch38',
    }],
    missed_checks: ['Ask customer when the AC was last serviced'],
    safety_concerns: ['Confirm MCB off before touching outdoor terminals'],
    model_identifier: 'gemini-3.5-flash-lite', latency_ms: 950,
  },
  challenger_checked_at: null,
}

const safetyLocked: SafetyState = {
  power_off_confirmed: false, tester_checked: false, unlocked: false,
  missing: ['power_off_confirmed', 'tester_checked'], expired: false, confirmed_at: null, expires_at: null, disclaimer: 'Technician statement only.',
}

const sampleSteps: RepairStep[] = [
  { id: 'st1', step_number: 1, title: 'Inspect indoor filter', instruction: 'Slide out and inspect filter.', kind: 'safe_action', requires_power_off: false, status: 'pending', locked: false, visual_media_id: null, completed_at: null },
]

describe('Red-Team Challenger UI & step gate', () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear() })
  beforeEach(() => { Element.prototype.scrollIntoView = () => undefined; signedIn() })

  function stubSession(diag: Diagnosis) {
    vi.spyOn(services.sessionService, 'get').mockResolvedValue(session)
    vi.spyOn(services.repairService, 'diagnosis').mockResolvedValue(diag)
    vi.spyOn(services.repairService, 'steps').mockResolvedValue(sampleSteps)
    vi.spyOn(services.repairService, 'safety').mockResolvedValue(safetyLocked)
    vi.spyOn(services.fileService, 'list').mockResolvedValue([])
    vi.spyOn(services.repairService, 'similar').mockResolvedValue({ mode: 'keyword', results: [] } as never)
    vi.spyOn(services.lookupService, 'expectedReadings').mockResolvedValue({ appliance_type: 'split_ac', disclaimer: '', items: [] })
  }

  it('shows bilingual objections, provenance details, and gates steps until I checked this is clicked', async () => {
    stubSession(diagDisagree)
    vi.spyOn(services.repairService, 'acknowledgeChallenger').mockResolvedValue({ ...diagDisagree, challenger_checked_at: '2026-11-28T00:05:00Z' })

    wrap(<RepairSessionPage />)
    expect(await screen.findByText(/Challenger disagreed/i)).toBeTruthy()
    expect(screen.getByText(/यह कम्प्रेशर की जगह फ्लेयर नट लीक भी हो सकता है/i)).toBeTruthy()
    expect(screen.getByText(/78% → 52%/)).toBeTruthy()
    expect(screen.getByText(/Challenger raised an objection/i)).toBeTruthy()
    expect(screen.queryByText(/Inspect indoor filter/i)).toBeNull()
    expect(screen.getByText(/Disagreed \(950 ms\)/i)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /I checked this/i }))
    await waitFor(() => expect(screen.getByText(/Checked by technician/i)).toBeTruthy())
    expect(screen.getByText(/Inspect indoor filter/i)).toBeTruthy()
  })

  it('shows Challenger unavailable non-blockingly when challenger timed out', async () => {
    stubSession({
      ...diagDisagree,
      challenger: {
        status: 'unavailable', agrees: null, objections: [], missed_checks: [], safety_concerns: [],
        revised_confidence: null, confidence_before: 0.78, model_identifier: null, latency_ms: 5001, error_code: 'AI_TIMEOUT',
      },
      challenger_checked_at: null,
    })

    wrap(<RepairSessionPage />)
    expect(await screen.findByText(/Challenger unavailable/i)).toBeTruthy()
    expect(screen.getByText(/Inspect indoor filter/i)).toBeTruthy()
  })

  it('EvaluationPage renders Red-Team Challenger held-out v2 summary', async () => {
    const split = {
      overall: { cases: 36, 'hit@1': 0.944, 'hit@3': 0.944, 'hit@6': 1.0, mrr: 0.958 },
      by_language: { en: { cases: 30, 'hit@1': 0.933, 'hit@3': 0.933, 'hit@6': 1.0, mrr: 0.95 } },
      by_appliance: { split_ac: { cases: 6, 'hit@1': 1.0, 'hit@3': 1.0, 'hit@6': 1.0, mrr: 1.0 } },
      misses_top3: [],
    }
    const retSuite = { appliance_selected: split, appliance_detected: split, appliance_detection_accuracy: 0.972, appliance_detection_misses: [] }
    const sfSuite = { cases: 12, unsafe_withheld: '12/12', recall_unsafe: 1.0, safe_shown: '11/12', false_positive_rate: 0.083, errors: [] }
    vi.spyOn(services.systemService, 'evaluation').mockResolvedValue({
      date: '2026-11-28',
      retrieval_channels: 'error code + PostgreSQL full-text',
      note: 'Eval note',
      development: { retrieval: retSuite, safety_filter: sfSuite },
      held_out: { retrieval: retSuite, safety_filter: sfSuite },
      held_out_v2: { retrieval: retSuite },
      challenger_holdout_v2: {
        date: '2026-11-28', dataset: 'held_out_v2', cases: 36, model: 'gemini-3.5-flash-lite',
        ok_count: 36, unavailable_count: 0, agrees_count: 32, disagrees_count: 4,
        agree_rate: 0.889, disagree_rate: 0.111, safety_concerns_flagged: 2,
        avg_latency_ms: 1420, median_latency_ms: 1350, max_latency_ms: 2800,
        disagreements_on_top_fault_miss: 2, disagreements_on_top_fault_hit: 2, agreements_on_top_fault_miss: 1,
        note: 'Summary note',
        disagreements: [{ id: 'v2-09', query: 'fridge not cooling', top_fault_hit: false, diag_hit: false, claim: 'Check defrost heater', why: 'No frost check done' }],
      },
    })

    render(
      <AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={['/evaluation']}><Routes><Route path="/evaluation" element={<EvaluationPage />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>,
    )
    expect(await screen.findByText(/Red-Team Challenger \(36 held-out v2 queries\)/i)).toBeTruthy()
    expect(screen.getByText('32/36')).toBeTruthy()
    expect(screen.getByText(/Check defrost heater/i)).toBeTruthy()
  })
})
