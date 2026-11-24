import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { Menu, SquarePen } from 'lucide-react'
import { DesktopSidebar, MobileDrawer } from './Sidebar'
import { Emblem, Wordmark } from '../common/Logo'
import { useApp } from '../../context/AppContext'
import { speech } from '../../services/speech'
import { useT } from '../../i18n'

export function AppLayout() {
  const [open, setOpen] = useState(false)
  const { newSession } = useApp()
  const nav = useNavigate()
  const t = useT()
  return (
    <div className="flex h-dvh-safe w-full overflow-hidden bg-bg">
      <DesktopSidebar />
      <MobileDrawer open={open} onClose={() => setOpen(false)} />
      <div className="relative flex min-w-0 flex-1 flex-col">
        <header className="glass z-20 flex items-center justify-between border-b border-line px-2 py-2 md:hidden" style={{ paddingTop: 'max(0.5rem, env(safe-area-inset-top))' }}>
          <button aria-label={t('nav.menu')} onClick={() => setOpen(true)} className="icon-btn"><Menu size={20} /></button>
          <button onClick={() => { speech.stop(); newSession(); nav('/') }} aria-label={t('nav.home')} className="flex items-center gap-2"><Emblem height={24} /><Wordmark height={12} /></button>
          <button aria-label={t('nav.newChat')} onClick={() => { speech.stop(); newSession(); nav('/chat') }} className="icon-btn"><SquarePen size={19} /></button>
        </header>
        <main className="relative min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
