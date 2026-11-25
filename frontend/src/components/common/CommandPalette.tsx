import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { FileText, HandHelping, HelpCircle, Home, LayoutDashboard, MessageSquare, Moon, PlayCircle, Search, Settings, SquarePen, Sun, Wrench } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useApp } from '../../context/AppContext'
import { usePrefs } from '../../context/PrefsContext'
import { sessionService } from '../../services'
import { speech } from '../../services/speech'
import { useT } from '../../i18n'
import type { RepairSession } from '../../types'
import { isMac, OPEN_PALETTE } from '../../utils/palette'


interface Item { id: string; group: string; label: string; hint?: string; icon: ReactNode; run: () => void }

/** Ctrl K (Cmd K on a Mac): go anywhere, start a chat, switch theme, or find a past repair by what was said in it. */
export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const [chats, setChats] = useState<RepairSession[]>([])
  const input = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const nav = useNavigate()
  const t = useT()
  const { user } = useAuth()
  const { newSession } = useApp()
  const { resolvedTheme, setTheme } = usePrefs()
  const manager = user?.role === 'manager' || user?.role === 'admin'

  useEffect(() => {
    const key = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen(o => !o) } }
    const ev = () => setOpen(true)
    window.addEventListener('keydown', key); window.addEventListener(OPEN_PALETTE, ev)
    return () => { window.removeEventListener('keydown', key); window.removeEventListener(OPEN_PALETTE, ev) }
  }, [])
  useEffect(() => { if (open) { setQ(''); setActive(0); setTimeout(() => input.current?.focus(), 20) } }, [open])
  // Past repairs are searched on the server, a moment after typing stops.
  useEffect(() => {
    if (!open) return
    let live = true
    const tm = setTimeout(() => { sessionService.mine(q, 6).then(p => { if (live) setChats(p.items) }).catch(() => undefined) }, q ? 180 : 0)
    return () => { live = false; clearTimeout(tm) }
  }, [open, q])

  const go = (to: string) => () => { speech.stop(); nav(to) }
  const items = useMemo<Item[]>(() => {
    const all: Item[] = [
      { id: 'new', group: 'Go to', label: t('nav.newChat'), icon: <SquarePen size={16} />, run: () => { speech.stop(); newSession(); nav('/chat') } },
      { id: 'home', group: 'Go to', label: t('nav.home'), icon: <Home size={16} />, run: () => { speech.stop(); newSession(); nav('/') } },
      ...(manager ? [{ id: 'dash', group: 'Go to', label: t('nav.manager'), icon: <LayoutDashboard size={16} />, run: go('/manager') },
        { id: 'senior', group: 'Go to', label: t('nav.senior'), icon: <HandHelping size={16} />, run: go('/senior') }] : []),
      { id: 'repairs', group: 'Go to', label: manager ? t('nav.teamRepairs') : t('nav.repairs'), icon: <Wrench size={16} />, run: go(manager ? '/history' : '/repairs') },
      { id: 'reports', group: 'Go to', label: t('nav.reports'), icon: <FileText size={16} />, run: go('/reports') },
      { id: 'demo', group: 'Go to', label: t('nav.demo'), icon: <PlayCircle size={16} />, run: go('/demo') },
      { id: 'settings', group: 'Go to', label: t('nav.settings'), icon: <Settings size={16} />, run: go('/settings') },
      { id: 'help', group: 'Go to', label: 'Help', icon: <HelpCircle size={16} />, run: go('/help') },
      { id: 'theme', group: 'Display', label: resolvedTheme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme', icon: resolvedTheme === 'dark' ? <Sun size={16} /> : <Moon size={16} />, run: () => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark') },
    ]
    const n = q.trim().toLowerCase()
    const fixed = n ? all.filter(i => i.label.toLowerCase().includes(n)) : all
    const recent = chats.map<Item>(c => ({ id: `chat-${c.id}`, group: n ? 'Repairs' : 'Recent repairs', label: c.title, hint: c.reference, icon: <MessageSquare size={16} />, run: go(`/chat/${c.id}`) }))
    return [...fixed, ...recent]  // pages that match come first; past repairs below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, chats, manager, resolvedTheme, t])

  const pick = (i: Item | undefined) => { if (!i) return; setOpen(false); i.run() }
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(items.length - 1, a + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(0, a - 1)) }
    else if (e.key === 'Enter') { e.preventDefault(); pick(items[active]) }
    else if (e.key === 'Escape') { e.preventDefault(); setOpen(false) }
  }
  useEffect(() => { listRef.current?.querySelector(`[data-i="${active}"]`)?.scrollIntoView?.({ block: 'nearest' }) }, [active])

  let last = ''
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[12vh]" role="dialog" aria-modal="true" aria-label="Go to">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }} className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={() => setOpen(false)} />
          <motion.div initial={{ opacity: 0, y: -8, scale: 0.985 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6, scale: 0.985 }} transition={{ duration: 0.14 }}
            className="popover relative w-full max-w-xl overflow-hidden">
            <div className="flex items-center gap-3 border-b border-line px-4">
              <Search size={17} className="shrink-0 text-ink-3" aria-hidden />
              <input ref={input} value={q} onChange={e => { setQ(e.target.value); setActive(0) }} onKeyDown={onKey} placeholder="Go to a page or find a repair"
                role="combobox" aria-expanded="true" aria-controls="palette-list" aria-activedescendant={items[active] ? `palette-${items[active].id}` : undefined} aria-label="Go to a page or find a repair"
                className="h-13 w-full bg-transparent py-3.5 text-[15px] text-ink outline-none placeholder:text-ink-3" />
              <span className="kbd">Esc</span>
            </div>
            <ul id="palette-list" ref={listRef} role="listbox" className="max-h-[52vh] overflow-y-auto p-2">
              {items.length === 0 && <li className="px-3 py-8 text-center text-sm text-ink-3">Nothing matches “{q}”.</li>}
              {items.map((i, k) => {
                const head = i.group !== last ? (last = i.group) : null
                return (
                  <li key={i.id} role="presentation">
                    {head && <p className="px-3 pb-1 pt-2.5 text-xs font-medium text-ink-3">{head}</p>}
                    <div id={`palette-${i.id}`} data-i={k} role="option" aria-selected={k === active} onMouseMove={() => setActive(k)} onClick={() => pick(i)}
                      className={`flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm ${k === active ? 'bg-surface-2 text-ink' : 'text-ink-2'}`}>
                      <span className={k === active ? 'text-accent' : 'text-ink-3'}>{i.icon}</span>
                      <span className="min-w-0 flex-1 truncate">{i.label}</span>
                      {i.hint && <span className="num text-xs text-ink-3">{i.hint}</span>}
                    </div>
                  </li>
                )
              })}
            </ul>
            <div className="flex items-center gap-4 border-t border-line px-4 py-2 text-xs text-ink-3">
              <span className="flex items-center gap-1.5"><span className="kbd">↑</span><span className="kbd">↓</span>move</span>
              <span className="flex items-center gap-1.5"><span className="kbd">Enter</span>open</span>
              <span className="ml-auto flex items-center gap-1.5"><span className="kbd">{isMac() ? '⌘' : 'Ctrl'}</span><span className="kbd">K</span>anywhere</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
