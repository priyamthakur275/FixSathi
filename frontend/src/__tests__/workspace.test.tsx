import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { AuthProvider, useAuth } from '../context/AuthContext'
import { AppProvider } from '../context/AppContext'
import { PrefsProvider } from '../context/PrefsContext'
import WelcomePage from '../pages/WelcomePage'
import RepairSessionPage from '../pages/RepairSessionPage'
import ManagerDashboard from '../pages/ManagerDashboard'
import { DiagnosisCard } from '../components/repair/DiagnosisCard'
import { ExpectedReadingsCard } from '../components/repair/ExpectedReadingsCard'
import { PartCard } from '../components/repair/PartCard'
import { SafetyPanel } from '../components/repair/SafetyPanel'
import * as services from '../services'
import type { Diagnosis, RepairSession, RepairStep, SafetyState } from '../types'

const wrap = (ui: ReactNode, path = '/') => render(
  <AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={[path]}><Routes><Route path="*" element={ui} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>
)

function signedInAs(role: 'technician' | 'manager', id = 'u1') {
  localStorage.setItem('fixsaathi.refresh', 'saved-refresh-token')
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ access_token: 'a', refresh_token: 'r2', expires_in: 900 }), { status: 200, headers: { 'content-type': 'application/json' } })))
  vi.spyOn(services.authService, 'currentUser').mockResolvedValue({ id, full_name: 'Asha Rao', email: 'asha@fixsaathi.in', role, preferred_language: 'English', organisation_id: 'org1', organisation_name: 'Snap Service', created_at: new Date().toISOString() } as never)
}

describe('Phase 2 UI redesign', () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear() })
  beforeEach(() => {
    Element.prototype.scrollIntoView = () => undefined
  })

  it('Home shows primary Speak CTA, appliance chips, and Continue your last repair card with Demo label', async () => {
    signedInAs('technician', 'u1')
    vi.spyOn(services.historyService, 'list').mockResolvedValue({
      items: [{
        id: 's1', reference: 'FS-101', title: 'Demo: Ceiling fan: burn marks', appliance_type: 'ceiling_fan',
        appliance_label: 'Ceiling fan', demo: true, issue_description: 'Burn marks at canopy', status: 'active',
        technician_id: 'u1', technician_name: 'Asha Rao', first_time_fix: null, started_at: new Date().toISOString(),
        completed_at: null, report_id: null,
      } satisfies RepairSession],
      total: 1, limit: 20, offset: 0,
    })
    const Gate = () => (useAuth().loading ? null : <WelcomePage />)
    wrap(<Gate />)
    expect(await screen.findByText('Speak the fault')).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'Split AC' })).toBeTruthy()
    expect(await screen.findByText('Continue your last repair')).toBeTruthy()
    expect(screen.getByText('Demo: scripted sample, not live AI')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Open workspace' }).getAttribute('href')).toBe('/session/s1')
  })

  it('DiagnosisCard shows AI estimate, source record, and toggles Why this? evidence', async () => {
    const u = userEvent.setup()
    const diag: Diagnosis = {
      id: 'd1', problem_summary: 'Fan hums and runs slow',
      faults: [{
        fault: 'Weak run capacitor',
        explanation: 'Loss of capacitance reduces starting torque.',
        confidence: 0.78,
        status: 'supported_by_records',
        record_ids: ['kb:fan-001'],
        evidence: [{ source: 'technician_statement', detail: 'Fan hums and spins slowly' }],
      }],
      recommended_checks: [], follow_up_questions: [], safety_requirements: [], requires_escalation: false,
      model_identifier: 'gemini-2.5-flash', created_at: new Date().toISOString(), confidence_note: 'AI estimate only',
      confirmed_findings: [], missing_information: [], knowledge_coverage: 'grounded',
      sources: [{ record_id: 'kb:fan-001', source_name: 'FixSaathi Field Guide', source_url: null, license: 'MIT', verification_status: 'technician_reviewed', match: 'keyword', related_category: false }],
    }
    render(<ul><DiagnosisCard fault={diag.faults[0]} sources={diag.sources} index={0} /></ul>)
    expect(screen.getByText('AI estimate')).toBeTruthy()
    expect(screen.getByText('78%')).toBeTruthy()
    expect(screen.getByText('kb:fan-001')).toBeTruthy()
    const btn = screen.getByRole('button', { name: /Why this\?/i })
    expect(btn.getAttribute('aria-expanded')).toBe('false')
    await u.click(btn)
    expect(btn.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('Fan hums and spins slowly')).toBeTruthy()
  })

  it('PartCard renders original SVG schematic clearly labelled not a photo', () => {
    const { container } = render(<PartCard title="Test capacitor" instruction="Check capacitor terminals" appliance="ceiling_fan" />)
    expect(container.querySelector('svg')).toBeTruthy()
    expect(screen.getByText(/Run \/ Start Capacitor/)).toBeTruthy()
    expect(screen.getByText(/Schematic diagram \(FixSaathi SVG\) — not a photo of your unit/)).toBeTruthy()
  })

  it('SafetyPanel triggers haptic cue on unlock transition', () => {
    const vib = vi.fn()
    Object.defineProperty(navigator, 'vibrate', { configurable: true, value: vib })
    const st = (unlocked: boolean): SafetyState => ({
      power_off_confirmed: unlocked, tester_checked: unlocked, unlocked, missing: unlocked ? [] : ['power_off_confirmed'],
      expired: false, confirmed_at: null, expires_at: null, disclaimer: '',
    })
    const { rerender } = render(<SafetyPanel state={st(false)} busy={false} canEdit onChange={() => undefined} />)
    expect(vib).not.toHaveBeenCalled()
    rerender(<SafetyPanel state={st(true)} busy={false} canEdit onChange={() => undefined} />)
    expect(vib).toHaveBeenCalledWith([30, 40, 60])
    expect(screen.getByRole('status').textContent).toContain('Circuit isolated')
  })

  it('RepairSessionPage shows sticky safety bar, guided stages, and keeps locked steps hidden', async () => {
    signedInAs('technician', 'u1')
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({
      id: 's1', reference: 'FS-101', title: 'Fan humming', appliance_type: 'ceiling_fan', appliance_label: 'Ceiling fan',
      issue_description: 'Fan hums', status: 'active', technician_id: 'u1', technician_name: 'Asha Rao',
      first_time_fix: null, started_at: new Date().toISOString(), completed_at: null, report_id: null,
    })
    vi.spyOn(services.fileService, 'list').mockResolvedValue([])
    vi.spyOn(services.repairService, 'diagnosis').mockResolvedValue({
      id: 'd1', problem_summary: 'Weak capacitor', faults: [{ fault: 'Weak capacitor', explanation: 'Hums', confidence: 0.8, evidence: [] }],
      recommended_checks: [], follow_up_questions: [], safety_requirements: [], requires_escalation: false,
      model_identifier: 'gemini', created_at: new Date().toISOString(), confidence_note: '', confirmed_findings: [],
      missing_information: [], knowledge_coverage: 'grounded', sources: [],
    })
    const steps: RepairStep[] = [
      { id: 'st1', step_number: 1, title: 'Open canopy', instruction: null, kind: 'power_sensitive', requires_power_off: true, status: 'pending', locked: true, visual_media_id: null, completed_at: null },
    ]
    vi.spyOn(services.repairService, 'steps').mockResolvedValue(steps)
    vi.spyOn(services.repairService, 'safety').mockResolvedValue({ power_off_confirmed: false, tester_checked: false, unlocked: false, missing: ['power_off_confirmed', 'tester_checked'], expired: false, confirmed_at: null, expires_at: null, disclaimer: '' })
    vi.spyOn(services.repairService, 'similar').mockResolvedValue({ mode: 'keyword', fallback_reason: null, results: [] })

    const Gate = () => (useAuth().loading ? null : <RepairSessionPage />)
    render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={['/session/s1']}><Routes><Route path="/session/:id" element={<Gate />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)
    const bar = await screen.findByRole('region', { name: 'Power safety status' })
    expect(within(bar).getByText('Live · Power steps locked')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Isolate the power to unlock/ })).toBeTruthy()
    expect(screen.queryByText(/Schematic diagram/)).toBeNull() // locked step shows no part card
  })

  it('ManagerDashboard renders repair funnel and real helpful-answer rate', async () => {
    signedInAs('manager', 'm1')
    vi.spyOn(services.dashboardService, 'load').mockResolvedValue({
      overview: {
        total_sessions: 4, completed: 2, active: 2, escalated: 0, open_escalations: 0,
        funnel: { sessions: 4, diagnosed: 3, isolated: 2, fixed_first_time: 1 },
        first_time_fix_rate: 0.5, first_time_fix_sample: 2, avg_repair_minutes: 22,
        avg_rating: 4.5, ratings_count: 2, guidance_correct_rate: 1.0,
        answers_rated: 5, answers_helpful: 4, answer_helpful_rate: 0.8,
        avg_ai_latency_ms: 1400, ai_cost_per_repair: null, ai_cost_note: '',
      },
      trend: [{ day: 'Thu', date: '2026-11-26', sessions: 4, completed: 2 }],
      technicians: [{ name: 'Asha Rao', sessions: 4, escalated: 0, completed: 2 }],
      ratings: [{ stars: '5', count: 2 }],
    })
    vi.spyOn(services.historyService, 'list').mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })
    const Gate = () => (useAuth().loading ? null : <ManagerDashboard />)
    wrap(<Gate />)
    const funnel = await screen.findByRole('region', { name: 'Repair funnel' })
    expect(within(funnel).getByText(/1\. Sessions started/)).toBeTruthy()
    expect(within(funnel).getByText(/3\. Safety isolated/)).toBeTruthy()
    expect(within(funnel).getByText(/4\. Fixed first time/)).toBeTruthy()
    expect(screen.getByText('4 of 5 rated helpful')).toBeTruthy()
  })

  it('reads nameplate with Gemini Vision, feeds retrieval, and saves technician correction', async () => {
    const u = userEvent.setup()
    signedInAs('technician', 'u1')
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({
      id: 's1', reference: 'FS-102', title: 'AC error', appliance_type: 'split_ac', appliance_label: 'Split AC',
      issue_description: 'indoor display shows CH38', status: 'active', technician_id: 'u1', technician_name: 'Asha Rao',
      first_time_fix: null, started_at: new Date().toISOString(), completed_at: null, report_id: null,
    })
    vi.spyOn(services.fileService, 'list').mockResolvedValue([
      { id: 'm1', kind: 'upload', mime_type: 'image/png', size_bytes: 1200, width: 320, height: 240, url: '/api/v1/media/m1', meta: {}, created_at: new Date().toISOString() },
    ])
    vi.spyOn(services.repairService, 'diagnosis').mockResolvedValue(null)
    vi.spyOn(services.repairService, 'steps').mockResolvedValue([])
    vi.spyOn(services.repairService, 'safety').mockResolvedValue({ power_off_confirmed: false, tester_checked: false, unlocked: false, missing: ['power_off_confirmed', 'tester_checked'], expired: false, confirmed_at: null, expires_at: null, disclaimer: '' })
    vi.spyOn(services.repairService, 'similar').mockResolvedValue({ mode: 'keyword', fallback_reason: null, results: [] })
    vi.spyOn(services.repairService, 'readNameplate').mockResolvedValue({
      status: 'ok',
      ai_error: null,
      extracted: {
        readable: true, appliance_type: 'split_ac', brand: 'LG', model: 'LS-Q18YNZA', error_code: 'CH38',
        serial_number: null, raw_text: 'LG LS-Q18YNZA CH38', confidence: 0.92, notes: null,
        verified_by_technician: false, source: 'gemini_vision',
      },
      retrieval: {
        coverage: 'grounded',
        error_codes_found: ['CH38'],
        error_codes_unknown: [],
        hits: [{
          record_id: 'mfr:lg-ch38', title: 'LG split ac: code CH38', appliance_type: 'split_ac',
          brand: 'LG', model: 'LS-Q18YNZA', error_code: 'CH38', symptoms: ['CH38 shown'],
          possible_faults: ['Low refrigerant charge'], source_name: 'LG Manual', verification_status: 'verified_source',
          match: 'error_code', related_category: false,
        }],
      },
    })
    const patchSpy = vi.spyOn(services.repairService, 'updateNameplate').mockResolvedValue({
      status: 'ok',
      ai_error: null,
      extracted: {
        readable: true, appliance_type: 'split_ac', brand: 'LG', model: 'LS-Q18YNZA', error_code: 'CH05',
        serial_number: null, raw_text: 'LG LS-Q18YNZA CH38', confidence: 0.92, notes: null,
        verified_by_technician: true, source: 'gemini_vision',
      },
      retrieval: {
        coverage: 'grounded',
        error_codes_found: ['CH05'],
        error_codes_unknown: [],
        hits: [{
          record_id: 'mfr:lg-ch05', title: 'LG split ac: code CH05', appliance_type: 'split_ac',
          brand: 'LG', model: null, error_code: 'CH05', symptoms: ['CH05 shown'],
          possible_faults: ['Communication wiring fault'], source_name: 'LG Manual', verification_status: 'verified_source',
          match: 'error_code', related_category: false,
        }],
      },
    })

    const Gate = () => (useAuth().loading ? null : <RepairSessionPage />)
    render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={['/session/s1']}><Routes><Route path="/session/:id" element={<Gate />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)

    const readBtn = await screen.findByRole('button', { name: /Read nameplate \/ code/i })
    await u.click(readBtn)
    expect(await screen.findByText('LG split ac: code CH38')).toBeTruthy()
    expect(screen.getByText('AI estimate · check & edit')).toBeTruthy()

    const codeInput = screen.getByLabelText('Error code') as HTMLInputElement
    expect(codeInput.value).toBe('CH38')
    await u.clear(codeInput)
    await u.type(codeInput, 'CH05')
    await u.click(screen.getByRole('button', { name: /Save & search records/i }))

    expect(patchSpy).toHaveBeenCalledWith('s1', expect.objectContaining({ brand: 'LG', model: 'LS-Q18YNZA', error_code: 'CH05' }))
    expect(await screen.findByText('LG split ac: code CH05')).toBeTruthy()
    expect(screen.getByText('Checked by technician')).toBeTruthy()
  })

  it('shows graceful fallback message and empty manual inputs when Gemini Vision is unavailable', async () => {
    const u = userEvent.setup()
    signedInAs('technician', 'u1')
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({
      id: 's1', reference: 'FS-103', title: 'AC error', appliance_type: 'split_ac', appliance_label: 'Split AC',
      issue_description: 'blinking light', status: 'active', technician_id: 'u1', technician_name: 'Asha Rao',
      first_time_fix: null, started_at: new Date().toISOString(), completed_at: null, report_id: null,
    })
    vi.spyOn(services.fileService, 'list').mockResolvedValue([
      { id: 'm1', kind: 'upload', mime_type: 'image/png', size_bytes: 1200, width: 320, height: 240, url: '/api/v1/media/m1', meta: {}, created_at: new Date().toISOString() },
    ])
    vi.spyOn(services.repairService, 'diagnosis').mockResolvedValue(null)
    vi.spyOn(services.repairService, 'steps').mockResolvedValue([])
    vi.spyOn(services.repairService, 'safety').mockResolvedValue({ power_off_confirmed: false, tester_checked: false, unlocked: false, missing: ['power_off_confirmed', 'tester_checked'], expired: false, confirmed_at: null, expires_at: null, disclaimer: '' })
    vi.spyOn(services.repairService, 'similar').mockResolvedValue({ mode: 'keyword', fallback_reason: null, results: [] })
    vi.spyOn(services.repairService, 'readNameplate').mockResolvedValue({
      status: 'unavailable',
      ai_error: { code: 'AI_NOT_CONFIGURED', message: 'Gemini API key is not configured.', hint: 'Enter the brand, model, or error code below to search repair records manually.' },
      extracted: null,
      retrieval: null,
    })

    const Gate = () => (useAuth().loading ? null : <RepairSessionPage />)
    render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={['/session/s1']}><Routes><Route path="/session/:id" element={<Gate />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)

    await u.click(await screen.findByRole('button', { name: /Read nameplate \/ code/i }))
    expect((await screen.findByRole('alert')).textContent).toContain('AI_NOT_CONFIGURED')
    expect((screen.getByLabelText('Brand') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('Error code') as HTMLInputElement).value).toBe('')
  })

  it('renders ExpectedReadingsCard as informational reference without live-work guidance', async () => {
    vi.spyOn(services.lookupService, 'expectedReadings').mockResolvedValue({
      appliance_type: 'ceiling_fan',
      disclaimer: 'Reference values only — never instructions to work on or probe live circuits.',
      items: [{
        id: 'cf-cap', appliance_type: 'ceiling_fan', parameter: 'Run capacitor value',
        hindi_name: 'रन कैपेसिटर', expected_range: '2.0 µF – 2.5 µF',
        out_of_range_meaning: 'Below 1.5 µF causes weak torque.', condition: 'isolated_and_discharged',
      }],
    })
    render(<ExpectedReadingsCard appliance="ceiling_fan" />)
    expect(await screen.findByText('Expected readings')).toBeTruthy()
    expect(screen.getByText('Reference only · Not live-work guidance')).toBeTruthy()
    expect(screen.getByText(/2.0 µF – 2.5 µF/)).toBeTruthy()
    expect(screen.getByText(/never instructions to work on or probe live circuits/)).toBeTruthy()
  })
})
