import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AirVent, Droplets, Fan, Microwave, Refrigerator, Sun, WashingMachine, Zap } from 'lucide-react'
import { Emblem } from '../components/common/Logo'
import { Composer } from '../components/composer/Composer'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { appliances, suggestions } from '../constants/prompts'
import { useT, type Key } from '../i18n'

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
  const fade = (d: number) => ({ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { delay: d, duration: 0.35, ease: 'easeOut' as const } })

  return (
    <div className="flex min-h-full flex-col items-center px-4 py-8 md:px-8 md:py-12">
      <div className="flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-8">
        <motion.div {...fade(0)} className="flex flex-col items-center gap-4 text-center">
          <Emblem height={64} />
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-ink-3">{t(greeting())}</p>
            <h1 className="text-3xl font-semibold tracking-tight md:text-[40px] md:leading-tight">{t('home.hello', { name: first })}</h1>
            <p className="text-[17px] text-ink-2">{t('home.sub')}</p>
          </div>
        </motion.div>

        <motion.div {...fade(0.06)} className="w-full">
          <div role="radiogroup" aria-label={t('home.appliance')} className="flex flex-wrap justify-center gap-2">
            {appliances.map(a => { const I = ICON[a.id]; const on = appliance === a.id
              return <button key={a.id} role="radio" aria-checked={on} onClick={() => setAppliance(on ? null : a.id)}
                className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-[13px] font-medium transition-colors ${on ? 'border-accent bg-accent/10 text-ink' : 'border-line bg-surface text-ink-2 hover:border-line-2 hover:text-ink'}`}>
                <I size={16} className={on ? 'text-accent' : 'text-ink-3'} aria-hidden />{t(`app.${a.id}` as Key)}</button> })}
          </div>
        </motion.div>

        <motion.div {...fade(0.1)} className="w-full">
          <Composer onSend={(text, a, channel) => go(text, a, undefined, channel)} autoFocus />
        </motion.div>

        <motion.div {...fade(0.16)} className="flex flex-wrap justify-center gap-2">
          {suggestions.map(s => <button key={s.key} onClick={() => go(s.prompt, [], s.appliance)} className="chip">{t(s.key)}</button>)}
        </motion.div>
      </div>
      <p className="mt-8 pb-1 text-center text-xs text-ink-3">{t('chat.disclaimer')}</p>
    </div>
  )
}
