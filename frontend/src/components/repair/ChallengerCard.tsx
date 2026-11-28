import { AlertTriangle, Check, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react'
import type { ChallengerResult } from '../../types'

interface Props {
  challenger: ChallengerResult
  checkedAt?: string | null
  canEdit: boolean
  busy: boolean
  onAcknowledge: () => void
}

const pct = (v?: number | null) => (typeof v === 'number' ? `${Math.round(v * 100)}%` : '—')

export function ChallengerCard({ challenger, checkedAt, canEdit, busy, onAcknowledge }: Props) {
  if (challenger.status === 'unavailable') {
    return (
      <aside aria-label="Red-Team Challenger" className="rounded-xl border border-line bg-surface-2/40 p-3.5 text-xs text-ink-2">
        <div className="flex items-center justify-between gap-2">
          <p className="font-semibold text-ink">Challenger review</p>
          <span className="rounded-full border border-line bg-surface px-2 py-0.5 text-[11px] text-ink-3">Challenger unavailable</span>
        </div>
        <p className="mt-1 text-ink-3">Second-pass adversarial verification could not run in time. Primary diagnosis and safety lock remain active.</p>
      </aside>
    )
  }

  const agreed = challenger.agrees === true
  const needsAck = challenger.agrees === false && !checkedAt

  return (
    <aside
      aria-label="Red-Team Challenger"
      className={`rounded-xl border p-3.5 text-sm ${agreed ? 'border-ok/35 bg-ok/[0.05]' : 'border-warn/45 bg-warn/[0.06]'}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {agreed ? <ShieldCheck size={16} className="shrink-0 text-ok" aria-hidden /> : <AlertTriangle size={16} className="shrink-0 text-warn" aria-hidden />}
          <span className="font-semibold text-ink">
            {agreed ? 'Challenger agreed · सहमत' : 'Challenger disagreed · असहमत'}
          </span>
        </div>
        <span className="num rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs text-ink-2">
          Confidence: {pct(challenger.confidence_before)} → {pct(challenger.revised_confidence)}
        </span>
      </div>

      {challenger.safety_concerns.length > 0 && (
        <div role="alert" className="mt-2.5 rounded-lg border border-crit/40 bg-crit/10 px-3 py-2 text-xs text-crit">
          <p className="flex items-center gap-1.5 font-semibold"><ShieldAlert size={14} className="shrink-0" aria-hidden />Safety concern flagged (power lock enforced):</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {challenger.safety_concerns.map((sc, i) => <li key={i}>{sc}</li>)}
          </ul>
        </div>
      )}

      {challenger.objections.length > 0 && (
        <ul className="mt-2.5 space-y-2 text-xs">
          {challenger.objections.map((ob, i) => (
            <li key={i} className="rounded-lg border border-line bg-surface p-2.5">
              {ob.claim_hi && <p className="font-medium text-ink">{ob.claim_hi}</p>}
              <p className={ob.claim_hi ? 'mt-0.5 text-ink-2' : 'font-medium text-ink'}>{ob.claim}</p>
              {ob.why_hi && <p className="mt-1 text-ink-2">{ob.why_hi}</p>}
              <p className="mt-0.5 text-ink-3">{ob.why}</p>
              {ob.evidence_id && (
                <span className="mt-1.5 inline-block rounded border border-line bg-surface-2 px-1.5 py-px font-mono text-[11px] text-ink-3">
                  {ob.evidence_id}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {challenger.missed_checks.length > 0 && (
        <div className="mt-2.5 text-xs">
          <p className="font-medium text-ink-2">Missed checks suggested:</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink-2">
            {challenger.missed_checks.map((mc, i) => <li key={i}>{mc}</li>)}
          </ul>
        </div>
      )}

      {challenger.agrees === false && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line/70 pt-2.5">
          {needsAck ? (
            <>
              <p className="text-xs text-ink-2">Review objections before unlocking repair steps.</p>
              {canEdit && (
                <button type="button" onClick={onAcknowledge} disabled={busy} className="btn btn-primary btn-sm !min-h-[44px]">
                  {busy ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  I checked this · मैंने जाँच लिया
                </button>
              )}
            </>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ok">
              <Check size={14} aria-hidden />Checked by technician
            </span>
          )}
        </div>
      )}
    </aside>
  )
}
