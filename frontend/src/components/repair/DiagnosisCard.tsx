import { useState } from 'react'
import { BookOpen, ChevronDown, ExternalLink, HelpCircle } from 'lucide-react'
import type { Fault, SourceRef } from '../../types'

const STATUS_LABEL: Record<NonNullable<Fault['status']>, string> = {
  supported_by_records: 'From repair records',
  possible_cause: 'Possible cause',
  unverified_hypothesis: 'Unverified hypothesis',
}

const EVIDENCE_LABEL: Record<string, string> = {
  observed_in_image: 'Seen in photo',
  technician_statement: 'You said',
  ai_inference: 'AI inference',
  unknown: 'Missing info',
}

const VERIFICATION_LABEL: Record<string, string> = {
  verified_source: 'Manufacturer documentation',
  technician_reviewed: 'Technician reviewed',
  unverified: 'Sourced record (unverified)',
  synthetic_demo: 'Demo sample',
}

/** Ranked fault card with an explicit "AI estimate" confidence bar, matched source records, and a one-tap "Why this?" drawer. */
export function DiagnosisCard({ fault, sources, index }: { fault: Fault; sources: SourceRef[]; index: number }) {
  const [open, setOpen] = useState(false)
  const pct = Math.round(fault.confidence * 100)
  const matched = (fault.record_ids ?? [])
    .map(id => sources.find(s => s.record_id === id))
    .filter((s): s is SourceRef => Boolean(s))
  const status = fault.status
  const badgeCls = status === 'supported_by_records'
    ? 'border-accent/40 bg-accent/10 text-accent'
    : status === 'possible_cause'
      ? 'border-line-2 bg-surface-2 text-ink-2'
      : 'border-warn/40 bg-warn/10 text-warn'

  return (
    <li className="rounded-2xl border border-line bg-bg/40 p-4 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="num inline-flex h-5 min-w-5 items-center justify-center rounded-md bg-surface-3 px-1.5 text-[11px] font-semibold text-ink-2">#{index + 1}</span>
            <p className="font-medium leading-snug text-ink">{fault.fault}</p>
            {status && <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${badgeCls}`}>{STATUS_LABEL[status]}</span>}
          </div>
        </div>
        <div className="shrink-0 text-right leading-tight">
          <span className="num block text-[16px] font-semibold text-ink">{pct}%</span>
          <span className="block text-[11px] font-medium text-ink-3">AI estimate</span>
        </div>
      </div>

      <div className="mt-2.5 h-2 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${fault.fault} AI estimate`}>
        <div className="fs-grow h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </div>

      <p className="mt-2.5 text-sm leading-relaxed text-ink-2">{fault.explanation}</p>

      {matched.length > 0 && (
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs text-ink-3">
          <BookOpen size={13} className="shrink-0 text-accent" aria-hidden />
          <span>From record:</span>
          {matched.map(s => (
            <span key={s.record_id} className="inline-flex items-center gap-1 rounded-full border border-line bg-surface px-2 py-0.5 text-ink-2">
              <span className="num font-medium">{s.record_id}</span>
              <span className="text-ink-3">· {s.source_name}</span>
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <button type="button" onClick={() => setOpen(v => !v)} aria-expanded={open}
          className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-2 transition-colors hover:border-line-2 hover:text-ink">
          <HelpCircle size={14} className="text-accent" aria-hidden />
          Why this?
          <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
        </button>
      </div>

      {open && (
        <div className="mt-3 space-y-2.5 rounded-xl border border-line bg-surface p-3.5 text-xs">
          {fault.evidence.length > 0 ? (
            <div>
              <p className="mb-1.5 font-semibold text-ink">Evidence used for this estimate</p>
              <ul className="space-y-1 text-ink-2">
                {fault.evidence.map((e, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="shrink-0 font-semibold text-ink">{EVIDENCE_LABEL[e.source] ?? e.source}:</span>
                    <span>{e.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-ink-2">No separate evidence bullets were returned; check the matched repair records below.</p>
          )}
          {matched.length > 0 && (
            <div className="border-t border-line pt-2">
              <p className="mb-1 font-semibold text-ink">Matched repair records</p>
              <ul className="space-y-1 text-ink-2">
                {matched.map(s => (
                  <li key={s.record_id} className="flex flex-wrap items-center gap-1.5">
                    <span className="num font-semibold text-ink">{s.record_id}</span>
                    <span>· {s.source_name}</span>
                    <span className="text-ink-3">({VERIFICATION_LABEL[s.verification_status] ?? s.verification_status}, {s.license})</span>
                    {s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-accent hover:underline">Source<ExternalLink size={11} /></a>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="border-t border-line pt-2 text-[11px] text-ink-3">Confidence ({pct}%) is an AI estimate, not a physical measurement. Verify with your own inspection.</p>
        </div>
      )}
    </li>
  )
}
