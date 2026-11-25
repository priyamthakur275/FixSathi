import { Check, Loader2, Lock, ShieldCheck } from 'lucide-react'
import type { SafetyState } from '../../types'
import { IsolatorSwitch } from './IsolatorSwitch'

interface Props { state: SafetyState | null; busy: boolean; canEdit: boolean; onChange: (power: boolean, tester: boolean) => void }

const time = (iso: string | null | undefined) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null

/** The server's safety gate, drawn as the breaker the technician has to switch off. Red is live and locked, green is isolated. */
export function SafetyPanel({ state, busy, canEdit, onChange }: Props) {
  const power = state?.power_off_confirmed ?? false
  const tester = state?.tester_checked ?? false
  const both = !!state?.unlocked
  const until = time(state?.expires_at)
  const row = (checked: boolean) => `group flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-sm transition-colors ${checked ? 'border-ok/40 bg-ok/[0.06]' : 'border-line bg-bg/40 hover:border-line-2'} has-[:disabled]:cursor-not-allowed`
  const tick = (checked: boolean) => `mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent ${checked ? 'border-ok bg-ok text-white' : 'border-line-2 bg-surface'}`
  return (
    <section id="safety" aria-labelledby="safety-h" className={`relative scroll-mt-20 overflow-hidden rounded-2xl border transition-colors duration-500 ${both ? 'border-ok/45' : 'border-crit/45'} bg-surface`}>
      {/* the wire: phase red until isolated, then earth green */}
      <div aria-hidden className={`h-1 w-full transition-colors duration-500 ${both ? 'bg-ok' : 'bg-crit'}`} />
      <div className="p-5 md:p-6">
        <div className="flex gap-5">
          <IsolatorSwitch isolated={both} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h2 id="safety-h" className="font-display text-[17px] leading-tight">Safety before opening anything</h2>
              {busy && <Loader2 size={15} className="mt-0.5 animate-spin text-ink-3" aria-label="Saving" />}
            </div>
            <p className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${both ? 'bg-ok/12 text-ok' : 'bg-crit/10 text-crit'}`}>
              {both ? <ShieldCheck size={13} aria-hidden /> : <Lock size={13} aria-hidden />}
              {both ? `Isolated${until ? `, unlocked until ${until}` : ''}` : 'Live: power steps locked by the server'}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-ink-2">FixSaathi can't measure voltage. These are <strong className="font-semibold text-ink">your own statements</strong>: only your tester proves a circuit is dead.</p>
          </div>
        </div>
        <div className="mt-5 space-y-2.5">
          <label className={row(power)}>
            <input type="checkbox" disabled={busy || !canEdit} className="peer sr-only" checked={power} onChange={e => onChange(e.target.checked, tester)} />
            <span aria-hidden className={tick(power)}>{power && <Check size={13} strokeWidth={3} />}</span>
            <span>I state that I have switched the power off at the MCB or isolator.</span>
          </label>
          <label className={row(tester)}>
            <input type="checkbox" disabled={busy || !canEdit} className="peer sr-only" checked={tester} onChange={e => onChange(power, e.target.checked)} />
            <span aria-hidden className={tick(tester)}>{tester && <Check size={13} strokeWidth={3} />}</span>
            <span>I state that I checked with my own tester and found no live line.</span>
          </label>
        </div>
        <p className={`mt-4 text-xs font-medium ${both ? 'text-ok' : 'text-crit'}`} role="status">
          {state?.expired ? 'Your earlier statements expired. Check again and record them again.'
            : both ? `Statements recorded. Power-sensitive steps are unlocked until ${until ?? 'they expire'}.`
              : 'Tick both to unlock power steps.'}
        </p>
        {!canEdit && <p className="mt-2 text-xs text-ink-3">Only the technician working on this session can record these.</p>}
      </div>
    </section>
  )
}
