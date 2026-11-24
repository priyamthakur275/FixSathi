import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { HandHelping, Home, LayoutDashboard, LogOut, MoreHorizontal, PanelLeftClose, PanelLeftOpen, Pencil, Search, Settings, SquarePen, Trash2, X } from 'lucide-react'
import { Emblem, Wordmark } from '../common/Logo'
import { ConfirmDialog, useDismiss } from '../common/Dialog'
import { useApp } from '../../context/AppContext'
import { useAuth } from '../../context/AuthContext'
import { sessionService } from '../../services'
import { speech } from '../../services/speech'
import { useT, type Key } from '../../i18n'
import type { RepairSession } from '../../types'

const GROUPS: { key: Key; test: (days: number) => boolean }[] = [
  { key: 'group.today', test: d => d === 0 }, { key: 'group.yesterday', test: d => d === 1 },
  { key: 'group.week', test: d => d >= 2 && d < 7 }, { key: 'group.older', test: d => d >= 7 },
]
/** Calendar days between the chat's start and today, in the device's time zone. */
function daysAgo(iso: string) {
  const a = new Date(iso); const b = new Date()
  return Math.round((new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime() - new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime()) / 86400000)
}

function useChats(q: string, version: number) {
  const [data, setData] = useState<RepairSession[] | null>(null)
  const [error, setError] = useState(false)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let live = true
    const t = setTimeout(() => {
      sessionService.mine(q).then(r => { if (live) { setData(r.items); setError(false) } }).catch(() => { if (live) setError(true) })
    }, q ? 220 : 0)
    return () => { live = false; clearTimeout(t) }
  }, [q, version, tick])
  return { data, error, retry: () => setTick(x => x + 1), setData }
}

function ChatRow({ s, active, onNavigate, onRename, onDelete }: { s: RepairSession; active: boolean; onNavigate?: () => void; onRename: (title: string) => Promise<void>; onDelete: () => void }) {
  const t = useT()
  const [menu, setMenu] = useState(false)
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(s.title)
  const btn = useRef<HTMLButtonElement>(null)
  const pop = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setMenu(false), [])
  useDismiss(menu, useMemo(() => [btn, pop], []), close)
  const saving = useRef(false)
  const save = async (e?: FormEvent) => {
    e?.preventDefault()
    if (saving.current) return  // Enter submits, then the input's blur fires as it unmounts
    saving.current = true
    const v = title.trim()
    setEditing(false)
    if (v && v !== s.title) await onRename(v).catch(() => setTitle(s.title)); else setTitle(s.title)
  }
  if (editing) {
    return (
      <form onSubmit={save} className="px-1 py-0.5">
        <label className="sr-only" htmlFor={`rn-${s.id}`}>{t('chat.rename')}</label>
        <input id={`rn-${s.id}`} autoFocus value={title} maxLength={160} onChange={e => setTitle(e.target.value)} onBlur={() => void save()}
          onKeyDown={e => { if (e.key === 'Escape') { setTitle(s.title); setEditing(false) } }}
          className="w-full rounded-lg border border-accent bg-surface px-2.5 py-1.5 text-[13.5px] text-ink outline-none" />
      </form>
    )
  }
  return (
    <div className={`group relative flex items-center rounded-lg transition-colors ${active ? 'bg-surface-2' : 'hover:bg-surface'}`}>
      <NavLink to={`/chat/${s.id}`} onClick={onNavigate} title={s.title} className={`min-w-0 flex-1 truncate py-2 pl-3 pr-8 text-[13.5px] ${active ? 'text-ink' : 'text-ink-2 group-hover:text-ink'}`}>{s.title}</NavLink>
      <button ref={btn} aria-label={`${t('chat.options')}: ${s.title}`} aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu(m => !m)}
        className={`absolute right-1 flex h-7 w-7 items-center justify-center rounded-md text-ink-3 hover:bg-surface-3 hover:text-ink ${menu || active ? 'opacity-100' : 'opacity-0 focus:opacity-100 group-hover:opacity-100'} max-md:opacity-100`}>
        <MoreHorizontal size={16} />
      </button>
      <AnimatePresence>
        {menu && (
          <motion.div ref={pop} role="menu" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}
            className="popover absolute right-1 top-9 z-40 w-40 p-1">
            <button role="menuitem" onClick={() => { setMenu(false); setTitle(s.title); saving.current = false; setEditing(true) }} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm hover:bg-surface-2"><Pencil size={15} className="text-ink-3" />{t('chat.rename')}</button>
            <button role="menuitem" onClick={() => { setMenu(false); onDelete() }} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm text-crit hover:bg-crit/10"><Trash2 size={15} />{t('chat.delete')}</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ProfileMenu({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const t = useT()
  const { user, logout } = useAuth()
  const { newSession } = useApp()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const btn = useRef<HTMLButtonElement>(null)
  const pop = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(open, useMemo(() => [btn, pop], []), close)
  if (!user) return null
  const isManager = user.role === 'manager' || user.role === 'admin'
  const go = (to: string) => { setOpen(false); onNavigate?.(); nav(to) }
  const signOut = async () => { setOpen(false); speech.stop(); await logout(); newSession(); nav('/login', { replace: true }) }
  const item = 'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm text-ink hover:bg-surface-2'
  const initial = (user.full_name.trim()[0] || '?').toUpperCase()
  return (
    <div className="relative">
      <button ref={btn} onClick={() => setOpen(o => !o)} aria-haspopup="menu" aria-expanded={open} aria-label={t('nav.account')}
        className={`flex w-full items-center gap-2.5 rounded-xl p-1.5 text-left transition-colors hover:bg-surface ${collapsed ? 'justify-center' : ''}`}>
        <span className="fs-accent-bg flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold text-white">{initial}</span>
        {!collapsed && <span className="min-w-0 leading-tight"><span className="block truncate text-[13.5px] font-medium">{user.full_name}</span><span className="block truncate text-[11.5px] text-ink-3">{t(`role.${user.role}` as Key)}</span></span>}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div ref={pop} role="menu" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.14 }}
            className={`popover absolute bottom-full z-50 mb-2 w-64 p-1.5 ${collapsed ? 'left-0' : 'inset-x-0 w-auto'}`}>
            <div className="border-b border-line px-2.5 pb-2.5 pt-1.5">
              <p className="truncate text-sm font-semibold">{user.full_name}</p>
              {user.email && <p className="truncate text-xs text-ink-2">{user.email}</p>}
              <p className="mt-1 text-xs text-ink-3">{t(`role.${user.role}` as Key)}{user.organisation_name ? ` · ${user.organisation_name}` : ''}</p>
            </div>
            <div className="pt-1">
              <button role="menuitem" onClick={() => go('/settings')} className={item}><Settings size={16} className="text-ink-3" />{t('nav.settings')}</button>
              {isManager && <button role="menuitem" onClick={() => go('/manager')} className={item}><LayoutDashboard size={16} className="text-ink-3" />{t('nav.manager')}</button>}
              {isManager && <button role="menuitem" onClick={() => go('/senior')} className={item}><HandHelping size={16} className="text-ink-3" />{t('nav.senior')}</button>}
              <button role="menuitem" onClick={() => void signOut()} className={item}><LogOut size={16} className="text-ink-3" />{t('nav.signOut')}</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Panel({ collapsed, onNavigate, onClose }: { collapsed: boolean; onNavigate?: () => void; onClose?: () => void }) {
  const t = useT()
  const { newSession, toggleCollapsed, sessionsVersion, refreshSessions, sessionId, setSessionTitle } = useApp()
  const nav = useNavigate()
  const loc = useLocation()
  const [searching, setSearching] = useState(false)
  const [q, setQ] = useState('')
  const chats = useChats(searching ? q : '', sessionsVersion)
  const [doomed, setDoomed] = useState<RepairSession | null>(null)
  const [deleting, setDeleting] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)

  const fresh = () => { speech.stop(); newSession(); onNavigate?.(); nav('/chat') }
  const home = () => { speech.stop(); newSession(); onNavigate?.(); nav('/') }
  const openSearch = () => { if (collapsed) toggleCollapsed(); setSearching(true); setTimeout(() => searchRef.current?.focus(), 30) }
  const closeSearch = () => { setSearching(false); setQ('') }

  const rename = async (s: RepairSession, title: string) => {
    const u = await sessionService.rename(s.id, title)
    chats.setData(d => d?.map(x => (x.id === s.id ? u : x)) ?? d)
    setSessionTitle(s.id, u.title)
  }
  const remove = async () => {
    if (!doomed) return
    setDeleting(true)
    try {
      await sessionService.remove(doomed.id)
      chats.setData(d => d?.filter(x => x.id !== doomed.id) ?? d)
      if (doomed.id === sessionId || loc.pathname === `/chat/${doomed.id}`) { speech.stop(); newSession(); nav('/') }
      refreshSessions(); setDoomed(null)
    } finally { setDeleting(false) }
  }

  const groups = useMemo(() => GROUPS.map(g => ({ ...g, items: (chats.data ?? []).filter(s => g.test(daysAgo(s.started_at))) })).filter(g => g.items.length), [chats.data])
  const row = 'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] text-ink-2 transition-colors hover:bg-surface hover:text-ink'
  const homeActive = loc.pathname === '/'

  return (
    <div className="flex h-full flex-col bg-bg-2 px-2.5 pb-3 pt-3.5">
      <div className={`mb-4 flex items-center ${collapsed ? 'justify-center' : 'justify-between'} px-1.5`}>
        <button onClick={home} aria-label={t('nav.home')} className="flex items-center gap-2">{collapsed ? <Emblem height={28} /> : <><Emblem height={28} /><Wordmark height={13} /></>}</button>
        {onClose ? <button aria-label={t('nav.close')} onClick={onClose} className="icon-btn"><X size={18} /></button>
          : !collapsed && <button onClick={toggleCollapsed} aria-label={t('nav.collapse')} title={t('nav.collapse')} className="icon-btn"><PanelLeftClose size={18} /></button>}
      </div>

      <div className={`space-y-0.5 ${collapsed ? 'flex flex-col items-center' : ''}`}>
        {collapsed && <button onClick={toggleCollapsed} aria-label={t('nav.expand')} title={t('nav.expand')} className="icon-btn mb-1"><PanelLeftOpen size={18} /></button>}
        <button onClick={fresh} title={t('nav.newChat')} aria-label={t('nav.newChat')} className={collapsed ? 'icon-btn' : `${row} font-medium !text-ink`}><SquarePen size={17} />{!collapsed && t('nav.newChat')}</button>
        <button onClick={home} title={t('nav.home')} aria-label={t('nav.home')} aria-current={homeActive ? 'page' : undefined} className={collapsed ? 'icon-btn' : `${row} ${homeActive ? 'bg-surface-2 !text-ink' : ''}`}><Home size={17} />{!collapsed && t('nav.home')}</button>
        {searching && !collapsed ? (
          <div className="relative px-0.5 pt-0.5">
            <Search size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-3" />
            <label className="sr-only" htmlFor="chat-search">{t('nav.search')}</label>
            <input id="chat-search" ref={searchRef} value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Escape') closeSearch() }} placeholder={t('chat.searchPlaceholder')}
              className="w-full rounded-lg border border-line-2 bg-surface py-2 pl-9 pr-8 text-[13.5px] text-ink outline-none placeholder:text-ink-3 focus:border-accent" />
            <button onClick={closeSearch} aria-label={t('chat.cancel')} className="absolute right-2 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded text-ink-3 hover:text-ink"><X size={14} /></button>
          </div>
        ) : <button onClick={openSearch} title={t('nav.search')} aria-label={t('nav.search')} className={collapsed ? 'icon-btn' : row}><Search size={17} />{!collapsed && t('nav.search')}</button>}
      </div>

      <nav className="-mr-1 mt-4 min-h-0 flex-1 overflow-y-auto pr-1" aria-label={t('nav.chats')}>
        {!collapsed && (<>
          {chats.data === null && !chats.error && <div className="space-y-2 px-2 pt-1">{[0, 1, 2, 3].map(i => <div key={i} className="skeleton h-6" />)}</div>}
          {chats.error && <p className="px-3 text-xs text-ink-3">{t('chat.loadError')} <button onClick={chats.retry} className="text-accent underline">{t('chat.retry')}</button></p>}
          {chats.data && chats.data.length === 0 && <p className="px-3 py-1 text-xs text-ink-3">{searching && q.trim() ? t('chat.noMatches', { q: q.trim() }) : t('chat.noChats')}</p>}
          {groups.map(g => (
            <div key={g.key} className="mb-3">
              <p className="px-3 pb-1 pt-1 text-[11.5px] font-medium text-ink-3">{t(g.key)}</p>
              <div className="space-y-px">
                {g.items.map(s => <ChatRow key={s.id} s={s} active={loc.pathname === `/chat/${s.id}`} onNavigate={onNavigate} onRename={title => rename(s, title)} onDelete={() => setDoomed(s)} />)}
              </div>
            </div>
          ))}
        </>)}
      </nav>

      <div className="mt-2 border-t border-line pt-2">
        <ProfileMenu collapsed={collapsed} onNavigate={onNavigate} />
      </div>

      <ConfirmDialog open={!!doomed} danger busy={deleting} title={t('chat.deleteTitle')} body={t('chat.deleteBody', { title: doomed?.title ?? '' })}
        confirm={t('chat.delete')} cancel={t('chat.cancel')} onConfirm={() => void remove()} onCancel={() => setDoomed(null)} />
    </div>
  )
}

export function DesktopSidebar() {
  const { collapsed } = useApp()
  return (
    <motion.aside animate={{ width: collapsed ? 64 : 268 }} transition={{ type: 'tween', duration: 0.2 }} className="hidden h-full shrink-0 border-r border-line md:block" aria-label="Sidebar">
      <Panel collapsed={collapsed} />
    </motion.aside>
  )
}

export function MobileDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="absolute inset-0 bg-black/55 backdrop-blur-sm" />
          <motion.div initial={{ x: -300 }} animate={{ x: 0 }} exit={{ x: -300 }} transition={{ type: 'tween', duration: 0.2 }} className="absolute inset-y-0 left-0 w-[84%] max-w-[300px] border-r border-line">
            <Panel collapsed={false} onNavigate={onClose} onClose={onClose} />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
