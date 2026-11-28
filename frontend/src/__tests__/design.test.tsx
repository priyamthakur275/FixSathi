import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { AppProvider } from '../context/AppContext'
import { PrefsProvider } from '../context/PrefsContext'
import { RepairProgress } from '../components/repair/RepairProgress'
import { SafetyPanel } from '../components/repair/SafetyPanel'
import { CommandPalette } from '../components/common/CommandPalette'
import { StatusPill } from '../components/common/ui'
import SettingsPage from '../pages/SettingsPage'
import * as services from '../services'
import type { SafetyState } from '../types'

describe('repair progress', () => {
  it('marks the first stage not done as the current step', () => {
    render(<RepairProgress isolateIndex={2} stages={[{ label: 'Describe', done: true }, { label: 'Diagnose', done: true }, { label: 'Isolate', done: false }, { label: 'Repair', done: false }, { label: 'Report', done: false }]} />)
    const steps = within(screen.getByRole('list', { name: 'Repair progress' })).getAllByRole('listitem')
    expect(steps[2].getAttribute('aria-current')).toBe('step')
    expect(steps.filter(s => s.getAttribute('aria-current')).length).toBe(1)
    expect(steps[0].textContent).toContain('(done)')
  })
})

describe('safety panel', () => {
  const st = (power: boolean, tester: boolean): SafetyState => ({ power_off_confirmed: power, tester_checked: tester, unlocked: power && tester, missing: [], expired: false, confirmed_at: null, expires_at: null, disclaimer: '' })
  it('says the power steps are locked until both statements are on record', () => {
    render(<SafetyPanel state={st(true, false)} busy={false} canEdit onChange={() => undefined} />)
    expect(screen.getByText('Live: power steps locked by the server')).toBeTruthy()
  })
  it('records a statement through the real checkbox', async () => {
    const onChange = vi.fn()
    render(<SafetyPanel state={st(true, false)} busy={false} canEdit onChange={onChange} />)
    await userEvent.setup().click(screen.getByLabelText('I state that I checked with my own tester and found no live line.'))
    expect(onChange).toHaveBeenCalledWith(true, true)
  })
  it('warns in red that MCB off is not enough for a microwave', () => {
    render(<SafetyPanel state={st(false, false)} busy={false} canEdit onChange={() => undefined} appliance="microwave_oven" />)
    expect(screen.getByRole('alert').textContent).toContain('switching off the MCB is not enough')
  })
  it('warns about the live DC side for rooftop solar', () => {
    render(<SafetyPanel state={st(false, false)} busy={false} canEdit onChange={() => undefined} appliance="rooftop_solar" />)
    expect(screen.getByRole('alert').textContent).toContain('DC side stays live')
  })
  it('shows no special warning for an ordinary appliance', () => {
    render(<SafetyPanel state={st(false, false)} busy={false} canEdit onChange={() => undefined} appliance="ceiling_fan" />)
    expect(screen.queryByRole('alert')).toBeNull()
  })
  it('shows isolated once both are recorded', () => {
    render(<SafetyPanel state={st(true, true)} busy={false} canEdit onChange={() => undefined} />)
    expect(screen.getByText(/^Isolated/)).toBeTruthy()
  })
})

describe('command palette', () => {
  let store: Record<string, string>
  beforeEach(() => {
    store = {}
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    Element.prototype.scrollIntoView = () => undefined
    vi.spyOn(services.sessionService, 'mine').mockResolvedValue({ items: [{ id: 's9', title: 'Kent RO beeping', reference: 'FS-9' }], total: 1, limit: 6, offset: 0 } as never)
  })
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

  const Where = () => <p data-testid="where">{useLocation().pathname}</p>
  const show = () => render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={['/']}><CommandPalette /><Routes><Route path="*" element={<Where />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)

  it('opens with Ctrl K, filters, and goes where Enter points', async () => {
    const u = userEvent.setup()
    show()
    expect(screen.queryByRole('dialog', { name: 'Go to' })).toBeNull()
    await u.keyboard('{Control>}k{/Control}')
    const box = await screen.findByRole('combobox', { name: 'Go to a page or find a repair' })
    await u.type(box, 'reports')
    await u.keyboard('{Enter}')
    expect(screen.getByTestId('where').textContent).toBe('/reports')
    await waitFor(() => expect(screen.queryByRole('combobox', { name: 'Go to a page or find a repair' })).toBeNull())
  })

  it('lists past repairs from the server and opens one', async () => {
    const u = userEvent.setup()
    show()
    await u.keyboard('{Control>}k{/Control}')
    await u.click(await screen.findByRole('option', { name: /Kent RO beeping/ }))
    expect(screen.getByTestId('where').textContent).toBe('/chat/s9')
  })
})

describe('design system: sunlight mode, language picker, and power-state colors', () => {
  it('supports sunlight mode and Hindi-first greeting in Settings, without Tamil in the picker', async () => {
    const u = userEvent.setup()
    render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter><SettingsPage /></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)
    await u.click(screen.getByRole('radio', { name: 'Sunlight' }))
    expect(document.documentElement.dataset.theme).toBe('sunlight')
    const langGroup = screen.getByRole('radiogroup', { name: 'Language' })
    const langs = within(langGroup).getAllByRole('radio').map(b => b.textContent)
    expect(langs.some(t => /English/.test(t || ''))).toBe(true)
    expect(langs.some(t => /Hindi/.test(t || ''))).toBe(true)
    expect(langs.some(t => /Kannada/.test(t || ''))).toBe(true)
    expect(langs.some(t => /Tamil/i.test(t || ''))).toBe(false)
    const hindiToggle = screen.getByRole('switch', { name: /Hindi-first greeting/ })
    await u.click(hindiToggle)
    expect((hindiToggle as HTMLInputElement).checked).toBe(true)
  })

  it('reserves green (ok) and red (crit) for power state only — never decorative status pills', () => {
    const { container } = render(<>
      <StatusPill status="active" />
      <StatusPill status="completed" />
      <StatusPill status="resolved" />
      <StatusPill status="not_resolved" />
    </>)
    expect(container.innerHTML).not.toMatch(/\b(bg-ok|text-ok|border-ok|bg-crit|text-crit|border-crit)\b/)
  })
})
