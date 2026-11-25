import { Loader2, Lock, ShieldAlert, ShieldCheck } from 'lucide-react'
import type { SafetyState } from '../../types'

interface Props { state: SafetyState | null; busy: boolean; canEdit: boolean; onChange: (power: boolean, tester: boolean) => void }

export function SafetyPanel({ state, busy, canEdit, onChange }: Props) {
  const power = state?.power_off_confirmed ?? false
  const tester = state?.tester_checked ?? false
  const both = !!state?.unlocked
  const box = 'mt-0.5 h-5 w-5 shrink-0 accent-[var(--color-accent)]'
  return (
    <section id="safety" aria-labelledby="safety-h" className={`scroll-mt-20 relative overflow-hidden rounded-[1.25rem] border p-5 md:p-6 transition-colors ${both ? 'border-ok/40 bg-gradient-to-b from-ok/[0.09] to-ok/[0.02]' : 'border-crit/40 bg-gradient-to-b from-crit/[0.09] to-crit/[0.02]'}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="safety-h" className="flex items-center gap-2.5 text-[15px] font-semibold">
          <span className={`flex h-8 w-8 items-center justify-center rounded-xl ${both ? 'bg-ok/15 text-ok' : 'bg-crit/15 text-crit'}`}>
            {both ? <ShieldCheck size={17} /> : <ShieldAlert size={17} />}
          </span>
          Safety before opening anything
          {busy && <Loader2 size={14} className="animate-spin text-ink-3" />}
        </h2>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${both ? 'border-ok/35 bg-ok/10 text-ok' : 'border-crit/35 bg-crit/10 text-crit'}`}>
          {both ? <ShieldCheck size={12} aria-hidden /> : <Lock size={12} aria-hidden />}
          {both ? 'UNLOCKED' : 'LOCKED · SERVER ENFORCED'}
        </span>
      </div>
      <p className="mt-2 text-sm text-ink-2">These are <strong className="text-ink">your own statements</strong>, recorded on the server for this session only. FixSaathi cannot measure voltage, control a tester or confirm that a circuit is dead. Always verify with your own tester.</p>
      <div className="mt-4 space-y-3">
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-bg/30 p-3 text-sm transition-colors hover:border-line-2"><input type="checkbox" disabled={busy || !canEdit} className={box} checked={power} onChange={e => onChange(e.target.checked, tester)} /><span>I state that I have switched the power off at the MCB or isolator.</span></label>
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-bg/30 p-3 text-sm transition-colors hover:border-line-2"><input type="checkbox" disabled={busy || !canEdit} className={box} checked={tester} onChange={e => onChange(power, e.target.checked)} /><span>I state that I checked with my own tester and found no live line.</span></label>
      </div>
      <p className={`mt-4 text-xs font-medium ${both ? 'text-ok' : 'text-crit'}`} role="status">
        {state?.expired ? 'Your earlier statements expired. Check again and record them again.'
          : both ? `Statements recorded. Power-sensitive steps are unlocked until ${state?.expires_at ? new Date(state.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'they expire'}.`
            : 'Power-sensitive steps stay locked on the server until both statements are recorded.'}
      </p>
      {!canEdit && <p className="mt-2 text-xs text-ink-3">Only the technician working on this session can record these.</p>}
    </section>
  )
}
