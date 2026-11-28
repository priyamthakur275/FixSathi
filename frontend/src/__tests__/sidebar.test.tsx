import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { AppProvider } from '../context/AppContext'
import { PrefsProvider } from '../context/PrefsContext'
import { DesktopSidebar } from '../components/sidebar/Sidebar'
import * as services from '../services'

// The rest of the app is reachable from the sidebar itself, not only from the account menu.
describe('workspace links', () => {
  let store: Record<string, string>
  beforeEach(() => {
    store = { 'fixsaathi.refresh': 'saved-refresh-token' }
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ access_token: 'a', refresh_token: 'r2', expires_in: 900 }), { status: 200, headers: { 'content-type': 'application/json' } })))
    vi.spyOn(services.sessionService, 'mine').mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 } as never)
  })
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

  const show = (role: string, path = '/') => {
    vi.spyOn(services.authService, 'currentUser').mockResolvedValue({ id: 'u1', full_name: 'Ravi', email: 'r@x.in', role, preferred_language: 'English' } as never)
    render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={[path]}><Routes><Route path="*" element={<DesktopSidebar />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)
    return screen.findByRole('navigation', { name: 'Workspace' })
  }

  it('a technician sees their repairs and reports in primary nav, with demos behind Offline backup', async () => {
    const nav = await show('technician')
    const links = within(nav).getAllByRole('link').map(a => [a.textContent, a.getAttribute('href')])
    expect(links).toEqual([['Fault finder', '/lookup'], ['My repairs', '/repairs'], ['Service reports', '/reports']])
    const backup = screen.getByRole('link', { name: 'Offline backup' })
    expect(backup.getAttribute('href')).toBe('/demo')
  })

  it('a manager also sees the team dashboard and the team history', async () => {
    const nav = await show('manager')
    expect(within(nav).getByRole('link', { name: 'Manager dashboard' }).getAttribute('href')).toBe('/manager')
    expect(within(nav).getByRole('link', { name: 'Team repairs' }).getAttribute('href')).toBe('/history')
  })

  it('marks the current page', async () => {
    const nav = await show('technician', '/reports')
    expect(within(nav).getByRole('link', { name: 'Service reports' }).getAttribute('aria-current')).toBe('page')
  })
})
