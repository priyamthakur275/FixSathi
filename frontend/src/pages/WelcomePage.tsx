import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AirVent, ChevronRight, Droplets, Fan, MessageSquare, Microwave, Refrigerator, Sun, SunMedium, WashingMachine, Wrench, Zap } from 'lucide-react'
import { Emblem } from '../components/common/Logo'
import { Composer } from '../components/composer/Composer'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { usePrefs } from '../context/PrefsContext'
import { appliances } from '../constants/prompts'
import { useLanguage, useT, type Key } from '../i18n'
import { historyService } from '../services'
import { DemoBadge, Skeleton, StatusPill } from '../components/common/ui'
import type { RepairSession } from '../types'

const ICON = { split_ac: AirVent, washing_machine: WashingMachine, refrigerator: Refrigerator, ceiling_fan: Fan, microwave_oven: Microwave, water_purifier: Droplets, mcb_electrical: Zap, rooftop_solar: Sun } as const

function greeting(): Key {
  const h = new Date().getHours()
  return h < 12 ? 'home.morning' : h < 17 ? 'home.afternoon' : 'home.evening'
}

export default function WelcomePage() {
  const { send, newSession } = useApp()
  const { user } = useAuth()
  const { theme, setTheme, hindiFirst, setHindiFirst } = usePrefs()
  const language = useLanguage()
  const t = useT()
  const first = user?.full_name.split(' ')[0] ?? ''
  const nav = useNavigate()
  const [appliance, setAppliance] = useState<string | null>(null)
  const go = (text: string, a: Parameters<typeof send>[1] = [], forced?: string, channel?: 'text' | 'voice') => {
    newSession(); void send(text, a, forced ?? appliance ?? undefined, channel); nav('/chat')
  }

  const [open, setOpen] = useState<RepairSession[] | null>(null)
  useEffect(() => {
    let live = true
    historyService.list(true)
      .then(p => { if (live) setOpen(p.items.filter(r => r.technician_id === user?.id).slice(0, 3)) })
      .catch(() => { if (live) setOpen([]) })
    return () => { live = false }
  }, [user?.id])

  const fade = (d: number) => ({ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { delay: d, duration: 0.3, ease: 'easeOut' as const } })
  const showHindi = hindiFirst || language === 'Hindi'
  const lastRepair = open?.[0]
  const moreOpen = open?.slice(1) ?? []
  const sunlightOn = theme === 'sunlight'

  return (
    <div className="flex min-h-full flex-col items-center px-4 py-5 md:px-8 md:py-10">
      <div className="flex w-full max-w-3xl flex-1 flex-col items-center gap-6">
        <div className="flex w-full flex-wrap items-center justify-end gap-2">
          <button type="button" onClick={() => setHindiFirst(!hindiFirst)} aria-pressed={hindiFirst}
            className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${hindiFirst ? 'border-accent bg-accent/12 text-accent' : 'border-line bg-surface text-ink-2 hover:text-ink'}`}>
            <span>हिन्दी greeting</span>
          </button>
          <button type="button" onClick={() => setTheme(sunlightOn ? 'system' : 'sunlight')} aria-pressed={sunlightOn}
            className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${sunlightOn ? 'border-accent bg-accent/12 text-accent' : 'border-line bg-surface text-ink-2 hover:text-ink'}`}>
            <SunMedium size={15} aria-hidden />
            <span>{t('settings.sunlight')}</span>
          </button>
        </div>

        <motion.div {...fade(0)} className="flex flex-col items-center gap-3 text-center">
          <Emblem height={48} />
          <div className="space-y-1.5">
            {!showHindi && <p className="text-sm font-medium text-ink-3">{t(greeting())}</p>}
            <h1 className="font-display text-[32px] leading-[1.06] md:text-[46px]">
              {showHindi ? t('home.hindiHello', { name: first }) : t('home.hello', { name: first })}
            </h1>
            <p className="text-[16px] text-ink-2">{showHindi ? t('home.hindiSub') : t('home.sub')}</p>
          </div>
        </motion.div>

        <motion.div {...fade(0.05)} className="w-full">
          <Composer hero onSend={(text, a, channel) => go(text, a, undefined, channel)} autoFocus />
        </motion.div>

        <motion.div {...fade(0.1)} className="w-full">
          <div role="radiogroup" aria-label={t('home.appliance')} className="flex flex-wrap justify-center gap-2">
            {appliances.map(a => {
              const I = ICON[a.id]
              const on = appliance === a.id
              return (
                <button key={a.id} role="radio" aria-checked={on} onClick={() => setAppliance(on ? null : a.id)}
                  className={`inline-flex min-h-[44px] items-center gap-2 rounded-full border px-3.5 py-2 text-[13px] font-medium shadow-[var(--shadow-card)] transition-colors ${on ? 'border-accent bg-accent/12 text-ink ring-2 ring-accent/20' : 'border-line bg-surface text-ink-2 hover:border-line-2 hover:text-ink'}`}>
                  <I size={16} className={on ? 'text-accent' : 'text-ink-3'} aria-hidden />
                  {t(`app.${a.id}` as Key)}
                </button>
              )
            })}
          </div>
        </motion.div>

        {open === null && (
          <div className="w-full space-y-2" aria-label="Loading open repairs">
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {lastRepair && (
          <motion.section {...fade(0.16)} aria-labelledby="open-h" className="w-full space-y-2.5">
            <div className="flex items-baseline justify-between px-1">
              <h2 id="open-h" className="text-sm font-semibold">{t('home.continueRepair')}</h2>
              <Link to="/repairs" className="text-xs font-medium text-ink-3 hover:text-ink">All open repairs</Link>
            </div>
            <div className="card card-hover p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-teal">{lastRepair.appliance_label}</span>
                  <span className="num rounded-md border border-line bg-surface-2 px-1.5 py-0.5 text-ink-3">{lastRepair.reference}</span>
                  {lastRepair.demo && <DemoBadge>Demo: scripted sample, not live AI</DemoBadge>}
                </div>
                <StatusPill status={lastRepair.status} />
              </div>
              <p className="mt-2 text-[15px] font-medium leading-snug">{lastRepair.title}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link to={`/chat/${lastRepair.id}`} className="btn btn-primary btn-sm"><MessageSquare size={15} />{t('home.resumeChat')}</Link>
                <Link to={`/session/${lastRepair.id}`} className="btn btn-sm"><Wrench size={15} />{t('home.openWorkspace')}</Link>
              </div>
            </div>
            {moreOpen.length > 0 && (
              <ul className="grid gap-2 sm:grid-cols-2">
                {moreOpen.map(r => (
                  <li key={r.id}>
                    <Link to={`/session/${r.id}`} className="card card-hover group flex h-full items-center justify-between gap-3 p-3.5">
                      <span className="min-w-0">
                        <span className="flex items-center gap-2 text-xs"><span className="font-semibold text-teal">{r.appliance_label}</span><span className="num text-ink-3">{r.reference}</span></span>
                        <span className="mt-0.5 block truncate text-sm font-medium">{r.title}</span>
                      </span>
                      <ChevronRight size={16} className="shrink-0 text-ink-3 transition-transform group-hover:translate-x-0.5" aria-hidden />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </motion.section>
        )}
      </div>
      <p className="mt-8 pb-1 text-center text-xs text-ink-3">{t('chat.disclaimer')}</p>
    </div>
  )
}
