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
})
