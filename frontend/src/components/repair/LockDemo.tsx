import { useEffect, useState } from 'react'
import { Check, Lock, RotateCcw, ShieldCheck } from 'lucide-react'
import { IsolatorSwitch } from './IsolatorSwitch'

const reduced = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** The sign-in page's one moving part: what a technician sees in a real session. A power step arrives locked; the two
 *  statements are recorded; the breaker drops and the step opens. Plays once, then waits for Replay. */
export function LockDemo() {
  const [phase, setPhase] = useState(reduced() ? 3 : 0)  // 0 locked, 1 first statement, 2 both, 3 step shown
  const [run, setRun] = useState(0)
  useEffect(() => {
    if (reduced()) return
    const t = [setTimeout(() => setPhase(1), 1400), setTimeout(() => setPhase(2), 2300), setTimeout(() => setPhase(3), 3000)]
    return () => t.forEach(clearTimeout)
  }, [run])
  const isolated = phase >= 2
  const stmt = (on: boolean, text: string) => (
    <li className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-[13px] transition-colors duration-300 ${on ? 'border-ok/40 bg-ok/[0.07] text-ink' : 'border-line bg-bg/50 text-ink-2'}`}>
      <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors duration-300 ${on ? 'border-ok bg-ok text-white' : 'border-line-2'}`}>{on && <Check size={11} strokeWidth={3} />}</span>{text}
    </li>
  )
  return (
    <figure className="relative overflow-hidden rounded-2xl border border-line-2 bg-surface shadow-[var(--shadow-lift)]" aria-label="Example: a power-sensitive step stays locked until both safety statements are recorded">
      <div aria-hidden className={`h-1 transition-colors duration-500 ${isolated ? 'bg-ok' : 'bg-crit'}`} />
      <div className="flex gap-5 p-5" aria-hidden>
        <IsolatorSwitch isolated={isolated} size={96} />
        <div className="min-w-0 flex-1">
          <p className="text-[12px] text-ink-3">Ceiling fan, burn marks at the hook</p>
          <p className="font-display mt-1 text-[16px]">2. Open the canopy</p>
          <div className="relative mt-2 min-h-[44px] text-[13px] leading-relaxed">
            <p className={`absolute inset-0 transition-opacity duration-500 ${phase >= 3 ? 'opacity-100' : 'opacity-0'}`}>Lower the canopy cover to expose the terminal block and the capacitor.</p>
            <p className={`absolute inset-0 flex items-start gap-1.5 font-medium text-crit transition-opacity duration-300 ${phase >= 3 ? 'opacity-0' : 'opacity-100'}`}><Lock size={14} className="mt-0.5 shrink-0" />Withheld by the server until the power is isolated.</p>
          </div>
          <ul className="mt-3 space-y-1.5">
            {stmt(phase >= 1, 'Switched off at the MCB')}
            {stmt(phase >= 2, 'Checked with my own tester')}
          </ul>
        </div>
      </div>
      <figcaption className="flex items-center justify-between gap-3 border-t border-line px-5 py-3 text-xs text-ink-3">
        <span className={`inline-flex items-center gap-1.5 font-medium ${isolated ? 'text-ok' : 'text-crit'}`}>{isolated ? <ShieldCheck size={13} aria-hidden /> : <Lock size={13} aria-hidden />}{isolated ? 'Isolated: step released' : 'Live: step locked'}</span>
        <button type="button" onClick={() => { setPhase(0); setRun(r => r + 1) }} className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 hover:bg-surface-2 hover:text-ink"><RotateCcw size={12} aria-hidden />Replay</button>
      </figcaption>
    </figure>
  )
}
