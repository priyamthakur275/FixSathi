import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AirVent, ChevronRight, Droplets, Fan, Microwave, Refrigerator, Sun, WashingMachine, Zap } from 'lucide-react'
import { Emblem } from '../components/common/Logo'
import { Composer } from '../components/composer/Composer'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { appliances, suggestions } from '../constants/prompts'
import { useT, type Key } from '../i18n'
import { historyService } from '../services'
import { StatusPill } from '../components/common/ui'
import type { RepairSession } from '../types'

const ICON = { split_ac: AirVent, washing_machine: WashingMachine, refrigerator: Refrigerator, ceiling_fan: Fan, microwave_oven: Microwave, water_purifier: Droplets, mcb_electrical: Zap, rooftop_solar: Sun } as const

function greeting(): Key {
  const h = new Date().getHours()
  return h < 12 ? 'home.morning' : h < 17 ? 'home.afternoon' : 'home.evening'
}

export default function WelcomePage() {
  const { send, newSession } = useApp()
  const { user } = useAuth()
  const t = useT()
  const first = user?.full_name.split(' ')[0] ?? ''
  const nav = useNavigate()
  const [appliance, setAppliance] = useState<string | null>(null)
  // Every message sent from Home starts a fresh conversation; it never continues the one that was open before.
  const go = (text: string, a: Parameters<typeof send>[1] = [], forced?: string, channel?: 'text' | 'voice') => {
    newSession(); void send(text, a, forced ?? appliance ?? undefined, channel); nav('/chat')
  }
  // Repairs this technician left open: one tap back into them, instead of hunting through the chat list.
  const [open, setOpen] = useState<RepairSession[]>([])
  useEffect(() => {
    let live = true
    historyService.list(true).then(p => { if (live) setOpen(p.items.filter(r => r.technician_id === user?.id).slice(0, 3)) }).catch(() => undefined)
    return () => { live = false }
  }, [user?.id])
  const fade = (d: number) => ({ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { delay: d, duration: 0.35, ease: 'easeOut' as const } })

  return (
    <div className="flex min-h-full flex-col items-center px-4 py-8 md:px-8 md:py-12">
      <div className="flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-8">
        <motion.div {...fade(0)} className="flex flex-col items-center gap-4 text-center">
          <Emblem height={52} />
          <div className="space-y-2">
            <p className="text-sm font-medium text-ink-3">{t(greeting())}</p>
            <h1 className="font-display text-[34px] leading-[1.05] md:text-[48px]">{t('home.hello', { name: first })}</h1>
            <p className="text-[17px] text-ink-2">{t('home.sub')}</p>
          </div>
        </motion.div>

        <motion.div {...fade(0.06)} className="w-full">
          <div role="radiogroup" aria-label={t('home.appliance')} className="flex flex-wrap justify-center gap-2">
            {appliances.map(a => { const I = ICON[a.id]; const on = appliance === a.id
              return <button key={a.id} role="radio" aria-checked={on} onClick={() => setAppliance(on ? null : a.id)}
                className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-[13px] font-medium shadow-[var(--shadow-card)] transition-colors ${on ? 'border-accent bg-accent/10 text-ink ring-2 ring-accent/15' : 'border-line bg-surface text-ink-2 hover:border-line-2 hover:text-ink'}`}>
                <I size={16} className={on ? 'text-accent' : 'text-ink-3'} aria-hidden />{t(`app.${a.id}` as Key)}</button> })}
          </div>
        </motion.div>

        <motion.div {...fade(0.1)} className="w-full">
          <Composer onSend={(text, a, channel) => go(text, a, undefined, channel)} autoFocus />
        </motion.div>

        <motion.div {...fade(0.16)} className="flex flex-wrap justify-center gap-2">
          {suggestions.map(s => <button key={s.key} onClick={() => go(s.prompt, [], s.appliance)} className="chip">{t(s.key)}</button>)}
        </motion.div>

        {open.length > 0 && (
          <motion.section {...fade(0.22)} aria-labelledby="open-h" className="w-full">
            <div className="mb-2.5 flex items-baseline justify-between px-1">
              <h2 id="open-h" className="text-sm font-semibold">Pick up where you left off</h2>
              <Link to="/repairs" className="text-xs text-ink-3 hover:text-ink">All open repairs</Link>
            </div>
            <ul className="grid gap-2 sm:grid-cols-3">
              {open.map(r => (
                <li key={r.id}>
                  <Link to={`/chat/${r.id}`} className="card card-hover group flex h-full flex-col gap-2 p-3.5">
                    <span className="flex items-center justify-between gap-2 text-xs"><span className="font-semibold text-teal">{r.appliance_label}</span><StatusPill status={r.status} /></span>
                    <span className="line-clamp-2 text-[13.5px] font-medium leading-snug">{r.title.replace(/^Demo: /, '')}</span>
                    <span className="mt-auto flex items-center justify-between text-xs text-ink-3"><span className="num">{r.reference}</span><ChevronRight size={14} className="transition-transform group-hover:translate-x-0.5" aria-hidden /></span>
                  </Link>
                </li>
              ))}
            </ul>
          </motion.section>
        )}
      </div>
      <p className="mt-8 pb-1 text-center text-xs text-ink-3">{t('chat.disclaimer')}</p>
    </div>
  )
}
