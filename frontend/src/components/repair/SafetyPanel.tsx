import { useEffect, useRef, useState } from 'react'
import { Check, Loader2, Lock, ShieldCheck, Zap } from 'lucide-react'
import type { SafetyState } from '../../types'
import { IsolatorSwitch } from './IsolatorSwitch'
import { useT, type Key } from '../../i18n'

interface Props { state: SafetyState | null; busy: boolean; canEdit: boolean; onChange: (power: boolean, tester: boolean) => void; appliance?: string }

/** Appliances where "MCB off, tester checked" is not the whole story. Shown in red above the two statements. */
const SPECIAL_HAZARD: Record<string, { title: Key; text: Key }> = {
  microwave_oven: { title: 'hazard.mwTitle', text: 'hazard.mwText' },
  rooftop_solar: { title: 'hazard.solarTitle', text: 'hazard.solarText' },
}

const time = (iso: string | null | undefined) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null

/** The server's safety gate, drawn as the breaker the technician has to switch off. Red is live and locked, green is isolated. */
export function SafetyPanel({ state, busy, canEdit, onChange, appliance }: Props) {
  const t = useT()
  const hk = appliance ? SPECIAL_HAZARD[appliance] : undefined
  const hazard = hk ? { title: t(hk.title), text: t(hk.text) } : undefined
  const power = state?.power_off_confirmed ?? false
  const tester = state?.tester_checked ?? false
  const both = !!state?.unlocked
  const until = time(state?.expires_at)
  const prevUnlocked = useRef(both)
  const [justUnlocked, setJustUnlocked] = useState(false)

  useEffect(() => {
    const was = prevUnlocked.current
    prevUnlocked.current = both
    if (!was && both) {
      try { navigator.vibrate?.([30, 40, 60]) } catch { /* vibration unsupported */ }
      setJustUnlocked(true)
      const tm = setTimeout(() => setJustUnlocked(false), 2600)
      return () => clearTimeout(tm)
    }
    if (!both) setJustUnlocked(false)
  }, [both])

  const row = (checked: boolean) => `group flex min-h-[52px] cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-sm transition-colors ${checked ? 'border-ok/45 bg-ok/[0.08]' : 'border-line bg-bg/40 hover:border-line-2'} has-[:disabled]:cursor-not-allowed`
  const tick = (checked: boolean) => `mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border transition-colors peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent ${checked ? 'border-ok bg-ok text-white' : 'border-line-2 bg-surface'}`
  return (
    <section id="safety" aria-labelledby="safety-h" className={`relative scroll-mt-20 overflow-hidden rounded-2xl border-2 transition-colors duration-500 ${both ? 'border-ok/55' : 'border-crit/55'} ${justUnlocked ? 'unlock-pulse' : ''} bg-surface shadow-[var(--shadow-card)]`}>
      {/* Power rail indicator: phase red until isolated, then earth green */}
      <div aria-hidden className={`h-1.5 w-full transition-colors duration-500 ${both ? 'bg-ok' : 'bg-crit'}`} />
      <div className="p-5 md:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-5">
          <div className={`flex items-center justify-center rounded-2xl border p-3 transition-colors duration-500 ${both ? 'border-ok/35 bg-ok/[0.06]' : 'border-crit/35 bg-crit/[0.06]'}`}>
            <IsolatorSwitch isolated={both} size={112} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h2 id="safety-h" className="font-display text-[18px] leading-tight">Safety before opening anything</h2>
              {busy && <Loader2 size={16} className="mt-0.5 animate-spin text-ink-3" aria-label="Saving" />}
            </div>
            <p className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${both ? 'bg-ok/15 text-ok' : 'bg-crit/12 text-crit'}`}>
              {both ? <ShieldCheck size={14} aria-hidden /> : <Lock size={14} aria-hidden />}
              {both ? `Isolated${until ? `, unlocked until ${until}` : ''}` : 'Live: power steps locked by the server'}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-ink-2">FixSaathi can&apos;t measure voltage. These are <strong className="font-semibold text-ink">your own statements</strong>: only your tester proves a circuit is dead.</p>
          </div>
        </div>
        {hazard && (
          <div role="alert" className="mt-4 flex gap-3 rounded-xl border-2 border-crit/60 bg-crit/[0.09] p-4">
            <Zap size={20} className="mt-0.5 shrink-0 text-crit" aria-hidden />
            <div className="text-sm leading-relaxed"><p className="font-semibold text-crit">{hazard.title}</p><p className="mt-0.5 text-ink">{hazard.text}</p></div>
          </div>
        )}
        <div className="mt-5 space-y-3">
          <label className={row(power)}>
            <input type="checkbox" disabled={busy || !canEdit} className="peer sr-only" checked={power} onChange={e => onChange(e.target.checked, tester)} />
            <span aria-hidden className={tick(power)}>{power && <Check size={14} strokeWidth={3} />}</span>
            <span className="leading-snug">I state that I have switched the power off at the MCB or isolator.</span>
          </label>
          <label className={row(tester)}>
            <input type="checkbox" disabled={busy || !canEdit} className="peer sr-only" checked={tester} onChange={e => onChange(power, e.target.checked)} />
            <span aria-hidden className={tick(tester)}>{tester && <Check size={14} strokeWidth={3} />}</span>
            <span className="leading-snug">I state that I checked with my own tester and found no live line.</span>
          </label>
        </div>
        <p className={`mt-4 text-xs font-semibold ${both ? 'text-ok' : 'text-crit'}`} role="status">
          {state?.expired ? 'Your earlier statements expired. Check again and record them again.'
            : justUnlocked ? 'Circuit isolated — power steps unlocked.'
              : both ? `Statements recorded. Power-sensitive steps are unlocked until ${until ?? 'they expire'}.`
                : 'Tick both to unlock power steps.'}
        </p>
        {!canEdit && <p className="mt-2 text-xs text-ink-3">Only the technician working on this session can record these.</p>}
      </div>
    </section>
  )
}
