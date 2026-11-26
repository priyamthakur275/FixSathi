import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, Loader2, Lock, Search, Wrench, X } from 'lucide-react'
import { lookupService, type LookupResponse, type LookupResult } from '../services'
import { useApp } from '../context/AppContext'
import { appliances } from '../constants/prompts'

const EXAMPLES = ['LG CH38', 'Samsung washer 5C', 'Fan hums but does not spin', 'Fridge not cooling', 'Kent RO beeping', 'Microwave sparks inside']
const VERIFIED: Record<string, string> = { verified_source: 'Manufacturer source', technician_reviewed: 'Technician reviewed', unverified: 'Unverified' }

function ResultCard({ r, onStart }: { r: LookupResult; onStart: () => void }) {
  const open = r.steps.filter(s => !s.locked)
  return (
    <article className="card overflow-hidden">
      <div className="card-pad">
        <div className="flex flex-wrap items-center gap-2 text-[13px]">
          {r.error_code && <span className="num rounded-md bg-ink px-2 py-0.5 text-[12px] font-semibold text-bg">{r.error_code}</span>}
          <span className="font-semibold text-teal">{r.appliance_label}</span>
          {r.brand && <span className="text-ink-2">{r.brand}{r.model ? ` ${r.model}` : ''}</span>}
          {r.related_category && <span className="text-xs text-ink-3">related appliance</span>}
        </div>
        <h2 className="font-display mt-2 text-[17px] leading-snug">{(r.symptoms[0] ?? r.title).replace(/^./, c => c.toUpperCase())}</h2>
        {r.symptoms.length > 1 && <p className="mt-1 text-sm text-ink-2">Also reported: {r.symptoms.slice(1).join('; ')}</p>}

        <div className="mt-4 grid gap-5 md:grid-cols-2">
          {r.possible_faults.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-ink-3">Likely causes</h3>
              <ul className="mt-1.5 space-y-1 text-sm">{r.possible_faults.map(f => <li key={f} className="flex gap-2"><span aria-hidden className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-3" />{f}</li>)}</ul>
            </div>
          )}
          {r.steps.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-ink-3">Checks</h3>
              {open.length > 0 && <ol className="mt-1.5 space-y-1.5 text-sm">{open.map((s, i) => <li key={i} className="flex gap-2"><span className="num w-4 shrink-0 text-ink-3">{i + 1}</span>{s.text}</li>)}</ol>}
              {r.locked_steps > 0 && (
                <p className="mt-2 flex items-start gap-2 text-sm text-crit"><Lock size={14} className="mt-0.5 shrink-0" aria-hidden />
                  {open.length ? `${r.locked_steps} more need` : r.locked_steps === 1 ? 'This check needs' : `These ${r.locked_steps} checks need`} the power isolated. Start a repair to see {r.locked_steps === 1 ? 'it' : 'them'}.</p>
              )}
            </div>
          )}
        </div>
        {r.components.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">{r.components.map(c => <span key={c} className="rounded-full border border-line px-2.5 py-0.5 text-xs text-ink-2">{c}</span>)}</div>
        )}
        {r.safety[0] && open.length !== r.steps.length && <p className="mt-4 text-xs leading-relaxed text-ink-3">{r.safety[0]}</p>}
      </div>
      <footer className="flex flex-col gap-3 border-t border-line bg-surface-2/40 px-5 py-3 text-xs sm:flex-row sm:items-center sm:justify-between md:px-6">
        <span className="flex min-w-0 flex-1 items-center gap-2 text-ink-3">
          {r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer" title={r.source_name} className="inline-flex min-w-0 items-center gap-1 hover:text-ink"><span className="truncate">{r.source_name}</span><ArrowUpRight size={12} className="shrink-0" aria-hidden /></a> : <span className="truncate">{r.source_name}</span>}
          <span className="shrink-0 rounded-full border border-line px-2 py-px">{VERIFIED[r.verification_status] ?? r.verification_status}</span>
        </span>
        <button onClick={onStart} className="btn btn-sm self-start sm:self-auto"><Wrench size={14} aria-hidden />Start a repair with this</button>
      </footer>
    </article>
  )
}

/** Error codes and symptoms, answered from the sourced records in a fraction of a second: no AI, no quota, works offline from Gemini. */
export default function FaultFinderPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const [appliance, setAppliance] = useState<string | null>(params.get('appliance'))
  const [data, setData] = useState<LookupResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const nav = useNavigate()
  const { newSession, send } = useApp()

  // Results follow the box as you type, a moment after you stop; the address keeps the search, so it can be shared or reopened.
  useEffect(() => {
    const term = q.trim()
    if (!term) { setParams({}, { replace: true }); return }
    let live = true
    const t = setTimeout(() => {
      setBusy(true); setErr(null)
      setParams({ q: term, ...(appliance ? { appliance } : {}) }, { replace: true })
      lookupService.search(term, appliance).then(d => { if (live) setData(d) })
        .catch(e => { if (live) setErr((e as Error).message || 'Search failed. Try again.') })
        .finally(() => { if (live) setBusy(false) })
    }, 220)
    return () => { live = false; clearTimeout(t) }
  }, [q, appliance, setParams])

  const start = (r: LookupResult) => {
    newSession()
    void send(r.error_code ? `${r.brand ? `${r.brand} ` : ''}${r.appliance_label} showing ${r.error_code}. ${q}` : q, [], r.appliance_type)
    nav('/chat')
  }
  const shown = q.trim() ? data : null

  return (
    <div className="page page-mid">
      <h1 className="font-display text-[26px] leading-tight md:text-[34px]">Fault finder</h1>
      <p className="mt-1.5 max-w-2xl text-sm text-ink-2">Type an error code or a symptom. Answers come straight from the sourced repair records, instantly, without the AI.</p>

      <div className="relative mt-6">
        <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-3" aria-hidden />
        <label htmlFor="lookup-q" className="sr-only">Error code or symptom</label>
        <input id="lookup-q" ref={input} autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="LG CH38, Samsung 5C, fan humming..." autoComplete="off"
          className="field !rounded-2xl !py-4 !pl-12 !pr-12 text-[16px] shadow-[var(--shadow-card)]" />
        {busy ? <Loader2 size={18} className="absolute right-4 top-1/2 -translate-y-1/2 animate-spin text-ink-3" aria-label="Searching" />
          : q && <button onClick={() => { setQ(''); input.current?.focus() }} aria-label="Clear" className="absolute right-3 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-ink-3 hover:bg-surface-2 hover:text-ink"><X size={16} /></button>}
      </div>
      <div role="radiogroup" aria-label="Appliance" className="-mx-1 mt-3 flex gap-1.5 overflow-x-auto px-1 pb-1">
        {[{ id: null, label: 'Any appliance' }, ...appliances].map(a => {
          const on = appliance === a.id
          return <button key={a.id ?? 'any'} role="radio" aria-checked={on} onClick={() => setAppliance(a.id)}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-[13px] transition-colors ${on ? 'border-accent bg-accent/10 font-medium text-ink' : 'border-line bg-surface text-ink-2 hover:text-ink'}`}>{a.label}</button>
        })}
      </div>

      {err && <p role="alert" className="mt-6 rounded-xl border border-crit/40 bg-crit/10 px-4 py-3 text-sm text-crit">{err}</p>}

      {!q.trim() && (
        <div className="mt-8">
          <p className="text-sm text-ink-3">Try</p>
          <div className="mt-2 flex flex-wrap gap-2">{EXAMPLES.map(x => <button key={x} onClick={() => setQ(x)} className="chip">{x}</button>)}</div>
        </div>
      )}

      {shown && (
        <section aria-live="polite" className="mt-6 space-y-4">
          <p className="text-sm text-ink-2">
            {shown.results.length ? `${shown.results.length} record${shown.results.length === 1 ? '' : 's'}` : 'No matching record'}
            {shown.appliance_type && !appliance ? ` for ${appliances.find(a => a.id === shown.appliance_type)?.label ?? shown.appliance_type}` : ''}
            {shown.brand ? `, ${shown.brand}` : ''}
          </p>
          {shown.error_codes_unknown.length > 0 && (
            <p className="rounded-xl border border-warn/40 bg-warn/10 px-4 py-3 text-sm text-warn">No record for {shown.error_codes_unknown.join(', ')}{shown.brand ? ` on ${shown.brand}` : ''}. Check the model's manual, or start a repair and describe what the unit does.</p>
          )}
          {shown.results.map(r => <ResultCard key={r.record_id} r={r} onStart={() => start(r)} />)}
          {shown.results.length === 0 && shown.error_codes_unknown.length === 0 && (
            <p className="py-6 text-sm text-ink-2">Nothing in the records matches “{q.trim()}”. Describe it in a chat instead and the AI will ask what it needs.</p>
          )}
        </section>
      )}
    </div>
  )
}
