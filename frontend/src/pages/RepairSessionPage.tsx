import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Camera, Check, ChevronLeft, Circle, Download, FileText, HandHelping, ImagePlus, Loader2, Lock, MessageSquare, ScanSearch, Sparkles, Stethoscope, Wand2 } from 'lucide-react'
import { CameraModal } from '../components/camera/CameraModal'
import { SafetyPanel } from '../components/repair/SafetyPanel'
import { AuthImage } from '../components/common/AuthImage'
import { ErrorState, Skeleton, StatusPill } from '../components/common/ui'
import { SourceList } from '../components/common/SourceList'
import { fileService, repairService, sessionService } from '../services'
import { DocChip } from '../components/composer/Composer'
import { openFile } from '../utils/openFile'
import type { ApiError } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { Attachment, ComponentResult, Diagnosis, MediaItem, RepairSession, RepairStep, SafetyState, SimilarResult } from '../types'

const CLOSED = ['completed', 'cancelled']
const btn = 'btn'
const h2 = 'flex items-center gap-2.5 text-[15px] font-semibold'
const ico = 'flex h-8 w-8 items-center justify-center rounded-xl bg-surface-3 text-teal'

export default function RepairSessionPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const nav = useNavigate()
  const [s, setS] = useState<RepairSession | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [media, setMedia] = useState<MediaItem[]>([])
  const [diag, setDiag] = useState<Diagnosis | null>(null)
  const [steps, setSteps] = useState<RepairStep[]>([])
  const [safety, setSafety] = useState<SafetyState | null>(null)
  const [comp, setComp] = useState<ComponentResult | null>(null)
  const [similar, setSimilar] = useState<SimilarResult | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ kind: 'error' | 'info'; text: string } | null>(null)
  const [camera, setCamera] = useState(false)
  const [escReason, setEscReason] = useState('')
  const [showEsc, setShowEsc] = useState(false)
  const [outcome, setOutcome] = useState<'resolved' | 'not_resolved' | 'escalated'>('resolved')
  const [ftf, setFtf] = useState<boolean | null>(null)
  const [notes, setNotes] = useState('')
  const [rating, setRating] = useState(0)

  const owner = !!s && !!user && s.technician_id === user.id
  const open = !!s && !CLOSED.includes(s.status)

  const load = useCallback(async () => {
    setLoadErr(null)
    try {
      const [ss, m, d, st, sf] = await Promise.all([sessionService.get(id), fileService.list(id), repairService.diagnosis(id), repairService.steps(id), repairService.safety(id)])
      setS(ss); setMedia(m); setDiag(d); setSteps(st); setSafety(sf)
      repairService.similar(id).then(setSimilar).catch(() => undefined)
    } catch (e) { setLoadErr((e as ApiError).message) }
  }, [id])
  useEffect(() => { void load() }, [load])

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setMsg(null)
    try { await fn() } catch (e) {
      const a = e as ApiError
      setMsg({ kind: 'error', text: a.code === 'SAFETY_CONFIRMATION_REQUIRED' ? 'Blocked by the server: record both safety statements first.' : a.message })
      if (a.code === 'SAFETY_CONFIRMATION_REQUIRED') setSafety(await repairService.safety(id))
    } finally { setBusy(null) }
  }
  const refreshSession = async () => setS(await sessionService.get(id))

  const addPhoto = (a: Attachment) => run('upload', async () => { const m = await fileService.upload(id, a.file, a.source === 'camera' ? 'capture' : 'upload', a.name); setMedia(x => [...x, m]) })
  const addDocs = (list: FileList | null) => run('upload', async () => {
    for (const f of Array.from(list ?? [])) {
      const c = fileService.check(f)
      if ('error' in c) throw new Error(c.error)
      const m = await fileService.upload(id, f, 'upload', f.name); setMedia(x => [...x, m])
    }
  })
  const isPhoto = (m: MediaItem) => m.kind !== 'generated' && m.kind !== 'document' && m.mime_type.startsWith('image/')
  const diagnose = () => run('diagnose', async () => { setDiag(await repairService.diagnose(id, media.filter(isPhoto).slice(-3).map(m => m.id))); await refreshSession() })
  const genSteps = () => run('steps', async () => { setSteps(await repairService.generateSteps(id)); await refreshSession() })
  const setSafe = (p: boolean, t: boolean) => run('safety', async () => { setSafety(await repairService.confirmSafety(id, p, t)); setSteps(await repairService.steps(id)) })
  const toggle = (x: RepairStep) => run(`step-${x.id}`, async () => {
    const u = x.status === 'completed' ? await repairService.reopenStep(id, x.id) : await repairService.completeStep(id, x.id)
    setSteps(st => st.map(y => y.id === u.id ? u : y))
  })
  const visual = (x: RepairStep) => run(`vis-${x.id}`, async () => { const m = await repairService.stepVisual(id, x.id); setMedia(v => v.some(y => y.id === m.id) ? v : [...v, m]); setSteps(st => st.map(y => y.id === x.id ? { ...y, visual_media_id: m.id } : y)) })
  const identify = (m: MediaItem) => run(`id-${m.id}`, async () => setComp(await repairService.identify(id, m.id)))
  const escalate = () => run('esc', async () => { await repairService.escalate(id, escReason); setShowEsc(false); setEscReason(''); await refreshSession(); setMsg({ kind: 'info', text: 'Senior technician support requested. A manager will see it under Senior Technician Support.' }) })
  const report = () => run('report', async () => {
    if (rating) await repairService.feedback(id, rating, null)
    const r = await repairService.report(id, outcome, outcome === 'resolved' ? ftf : null, notes); nav(`/reports/${r.id}`)
  })

  if (loadErr) return <div className="mx-auto max-w-3xl px-4 py-10"><ErrorState message={loadErr} onRetry={() => void load()} /></div>
  if (!s) return <div className="mx-auto max-w-6xl space-y-4 px-4 py-8 md:px-8"><Skeleton className="h-12 w-1/2" /><Skeleton className="h-64" /></div>

  const done = steps.filter(x => x.status === 'completed').length
  const pct = steps.length ? Math.round(done / steps.length * 100) : 0
  const photos = media.filter(isPhoto)
  const docs = media.filter(m => m.kind === 'document')

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8">
      <Link to={`/chat/${id}`} className="mb-5 inline-flex items-center gap-1 text-sm text-ink-2 transition-colors hover:text-ink"><ChevronLeft size={16} />Back to chat</Link>
      {s.demo && <div role="note" className="mb-4 rounded-2xl border border-warn/50 bg-warn/10 px-4 py-3 text-sm text-warn"><b>Demo scenario.</b> Diagnosis, steps and replies here are scripted sample content, not live AI. The safety lock, logging and report are the real server code.</div>}
      <header className="card card-pad mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="section-label"><span className="text-teal">{s.appliance_label}</span> · Session {s.reference}</p>
          <h1 className="mt-1.5 text-xl font-semibold leading-snug md:text-2xl">{s.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2"><StatusPill status={s.status} />{s.technician_name && !owner && <span className="text-xs text-ink-2">Technician: {s.technician_name}</span>}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className={btn} onClick={() => nav(`/chat/${id}`)}><MessageSquare size={16} />Chat</button>
          <button className={btn} disabled={busy === 'pdf'} onClick={() => run('pdf', () => sessionService.downloadPdf(id, s.reference))}>{busy === 'pdf' ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}PDF</button>
          {owner && open && s.status !== 'escalated' && <button onClick={() => setShowEsc(v => !v)} className="btn btn-warn"><HandHelping size={16} />Ask a senior technician</button>}
          {s.report_id && <Link to={`/reports/${s.report_id}`} className={btn}><FileText size={16} />Report</Link>}
        </div>
      </header>
      {showEsc && (
        <div className="mb-6 flex flex-col gap-2 rounded-2xl border border-warn/30 bg-warn/5 p-4 sm:flex-row">
          <label className="sr-only" htmlFor="esc">Reason</label>
          <input id="esc" value={escReason} onChange={e => setEscReason(e.target.value)} placeholder="Why do you need a senior? e.g. burnt smell in canopy" className="field flex-1 !py-2.5 text-sm" />
          <button disabled={escReason.trim().length < 3 || busy === 'esc'} onClick={escalate} className="btn !border-0 !bg-warn font-semibold !text-white">Send request</button>
        </div>
      )}
      {msg && <p role={msg.kind === 'error' ? 'alert' : 'status'} className={`mb-6 rounded-2xl border px-4 py-3 text-sm ${msg.kind === 'error' ? 'border-crit/40 bg-crit/10 text-crit' : 'border-teal/40 bg-teal/10 text-ink'}`}>{msg.text}</p>}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <div className="space-y-6">
          <section aria-labelledby="insp-h" className="card card-pad">
            <h2 id="insp-h" className={`${h2} mb-4`}><span className={ico}><Camera size={16} /></span>Visual inspection</h2>
            {photos.length === 0 ? (
              <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line-2 bg-surface/40 px-6 py-10 text-center">
                <Camera className="text-ink-3" /><p className="text-sm text-ink-2">No photos yet. Show the appliance with your camera or upload a photo.</p>
                {owner && open && <button onClick={() => setCamera(true)} className="btn btn-primary"><ImagePlus size={16} />Show me the appliance</button>}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  {photos.map(m => (
                    <div key={m.id} className="w-36">
                      <AuthImage src={m.url} alt="Appliance photo" className="h-32 w-36 rounded-2xl border border-line" box={comp?.media_id === m.id ? comp.box : null} label={comp?.media_id === m.id ? comp.component_name : null} />
                      {owner && open && <button onClick={() => identify(m)} disabled={!!busy} className="mt-1 inline-flex items-center gap-1 text-xs text-teal disabled:opacity-50">{busy === `id-${m.id}` ? <Loader2 size={12} className="animate-spin" /> : <ScanSearch size={12} />}Identify component</button>}
                    </div>
                  ))}
                  {owner && open && <button onClick={() => setCamera(true)} aria-label="Add another photo" className="flex h-32 w-32 items-center justify-center rounded-2xl border border-dashed border-line-2 text-ink-2 transition-colors hover:border-teal/60 hover:bg-surface-2 hover:text-teal"><ImagePlus /></button>}
                </div>
                {comp && <div className="rounded-2xl border border-teal/25 bg-teal/[0.05] p-3.5 text-sm"><p className="font-medium">{comp.found ? comp.component_name : 'Not identified'}</p><p className="text-ink-2">{comp.explanation}</p>{comp.uncertainty && <p className="mt-1 text-xs text-ink-3">{comp.uncertainty}</p>}<p className="mt-1 text-xs text-ink-3">{comp.note}</p></div>}
              </div>
            )}
            <div className="mt-5 border-t border-line pt-4">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="section-label">Documents{docs.length ? ` (${docs.length})` : ''}</p>
                {owner && open && <label className="btn btn-sm cursor-pointer"><FileText size={13} />Add PDF or document
                  <input type="file" multiple hidden data-testid="workspace-docs" accept=".pdf,.docx,.txt,.csv,.md,.log" onChange={e => { void addDocs(e.currentTarget.files); e.currentTarget.value = '' }} /></label>}
              </div>
              {docs.length === 0 ? <p className="text-xs text-ink-3">Attach a manual page, service sheet or notes. They are also added from chat.</p>
                : <div className="flex flex-wrap gap-2">{docs.map(d => { const name = String(d.meta.filename ?? 'Document')
                    return <DocChip key={d.id} name={name} size={d.size_bytes} onOpen={() => void openFile({ id: d.id, url: d.url, server: true, kind: 'document', name, mime: d.mime_type }).catch(() => setMsg({ kind: 'error', text: 'Could not open that file.' }))} /> })}</div>}
            </div>
            {busy === 'upload' && <p className="mt-3 flex items-center gap-2 text-xs text-ink-2"><Loader2 size={12} className="animate-spin text-teal" />Uploading...</p>}
          </section>

          <section aria-labelledby="diag-h" className="card card-pad">
            <div className="mb-4 flex items-center justify-between gap-2"><h2 id="diag-h" className={h2}><span className={ico}><Stethoscope size={16} /></span>Suspected faults</h2>
              {owner && open && <button onClick={diagnose} disabled={!!busy} className={btn}>{busy === 'diagnose' ? <Loader2 size={15} className="animate-spin" /> : <Stethoscope size={15} />}{diag ? 'Re-run diagnosis' : 'Run diagnosis'}</button>}</div>
            {!diag && <p className="text-sm text-ink-2">No diagnosis yet. Describe the issue in chat or add a photo, then run the diagnosis.</p>}
            {diag && (<>
              <p className="mb-2 text-sm text-ink-2">{diag.problem_summary}</p>
              <p className={`mb-2 inline-flex rounded-full border px-2.5 py-0.5 text-xs ${diag.knowledge_coverage === 'grounded' ? 'border-ok/40 text-ok' : diag.knowledge_coverage === 'partial' ? 'border-warn/40 text-warn' : 'border-crit/40 text-crit'}`}>
                {diag.knowledge_coverage === 'grounded' ? 'Backed by repair records' : diag.knowledge_coverage === 'partial' ? 'Partly backed by repair records' : 'No matching repair record: treat as unverified'}
              </p>
              {diag.confirmed_findings?.length > 0 && <p className="mb-2 text-sm"><span className="text-ink-2">Confirmed: </span>{diag.confirmed_findings.join('; ')}</p>}
              <ul className="space-y-2.5">
                {diag.faults.map(f => {
                  const pctc = Math.round(f.confidence * 100)
                  return (
                    <li key={f.fault} className="rounded-2xl border border-line bg-surface/50 p-4">
                      <div className="flex items-center justify-between gap-3"><p className="font-medium">{f.fault}{f.status && <span className={`ml-2 rounded-full border px-2 py-px text-[11px] font-normal ${f.status === 'supported_by_records' ? 'border-ok/40 text-ok' : f.status === 'possible_cause' ? 'border-line text-ink-2' : 'border-warn/40 text-warn'}`}>{({ supported_by_records: 'from records', possible_cause: 'possible cause', unverified_hypothesis: 'unverified' })[f.status]}</span>}</p><span className="shrink-0 whitespace-nowrap text-sm tabular-nums text-ink-2">{pctc}% (AI estimate)</span></div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={pctc} aria-valuemin={0} aria-valuemax={100} aria-label={`${f.fault} AI estimate`}><div className="fs-grad-bg h-full rounded-full" style={{ width: `${pctc}%` }} /></div>
                      <p className="mt-2 text-sm text-ink-2">{f.explanation}</p>
                      {f.evidence.length > 0 && <ul className="mt-1 space-y-0.5 text-xs text-ink-3">{f.evidence.map((e, i) => <li key={i}><span className="text-ink-2">{({ observed_in_image: 'Seen in photo', technician_statement: 'You said', ai_inference: 'AI inference', unknown: 'Unknown' })[e.source]}:</span> {e.detail}</li>)}</ul>}
                    </li>)
                })}
              </ul>
              {diag.follow_up_questions.length > 0 && <div className="mt-2 text-sm"><p className="text-ink-2">Questions to answer:</p><ul className="list-disc pl-5">{diag.follow_up_questions.map(q => <li key={q}>{q}</li>)}</ul></div>}
              {diag.missing_information?.length > 0 && <div className="mt-2 text-sm"><p className="text-ink-2">Still unknown:</p><ul className="list-disc pl-5">{diag.missing_information.map(q => <li key={q}>{q}</li>)}</ul></div>}
              {(diag.required_tools?.length ?? 0) > 0 && <p className="mt-2 text-sm"><span className="text-ink-2">Tools needed:</span> {diag.required_tools!.join(', ')}</p>}
              {diag.sources?.length > 0 && <SourceList sources={diag.sources} />}
              {diag.requires_escalation && <p className="mt-3 rounded-xl border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">The AI recommends a senior technician for this fault.{diag.escalation_reason ? ` ${diag.escalation_reason}` : ''}</p>}
              <p className="mt-3 text-xs text-ink-3">{diag.confidence_note} Model: {diag.model_identifier}</p>
            </>)}
          </section>

          {similar && similar.results.length > 0 && (
            <section aria-labelledby="sim-h" className="card card-pad">
              <h2 id="sim-h" className={`${h2} mb-2`}><span className={ico}><FileText size={16} /></span>Similar past repairs</h2>
              <p className="mb-2 text-xs text-ink-3">Search mode: {similar.mode}{similar.fallback_reason ? ` (${similar.fallback_reason})` : ''}</p>
              <ul className="divide-y divide-line text-sm">{similar.results.map(r => (
                <li key={r.source_id} className="py-2">{r.source_type === 'session' && r.report_id ? <Link className="font-medium hover:text-teal" to={`/reports/${r.report_id}`}>{r.reference}: {r.title}</Link> : <span className="font-medium">{r.title}</span>}<p className="text-ink-2">{r.snippet}</p><p className="text-xs text-ink-3">{r.why}</p></li>
              ))}</ul>
            </section>
          )}
        </div>

        <div className="space-y-6">
          <SafetyPanel state={safety} busy={busy === 'safety'} canEdit={owner && open} onChange={setSafe} />
          <section aria-labelledby="steps-h" className="card card-pad">
            <div className="mb-3 flex items-center justify-between gap-2"><h2 id="steps-h" className={h2}><span className={ico}><Wand2 size={16} /></span>Repair guidance</h2>
              <div className="flex items-center gap-3"><span className="text-sm text-ink-2">{done}/{steps.length} done</span>
                {owner && open && diag && done === 0 && <button onClick={genSteps} disabled={!!busy} className={btn}>{busy === 'steps' ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />}{steps.length ? 'Regenerate' : 'Generate steps'}</button>}</div></div>
            <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Step progress"><div className="fs-grad-bg h-full rounded-full transition-all" style={{ width: `${pct}%` }} /></div>
            {steps.length === 0 && <p className="text-sm text-ink-2">{diag ? 'Generate steps from the diagnosis, or get them live by voice.' : 'Steps appear after a diagnosis.'}</p>}
            <ol className="space-y-2">
              {steps.map(x => {
                const isDone = x.status === 'completed'
                const vis = x.visual_media_id ? media.find(m => m.id === x.visual_media_id) : undefined
                return (
                  <li key={x.id} className={`rounded-2xl border p-4 transition-colors ${x.locked ? 'border-line bg-bg/40 opacity-75' : isDone ? 'border-ok/25 bg-ok/[0.04]' : 'border-line-2 bg-surface/60'}`}>
                    <div className="flex items-start gap-3">
                      <button disabled={!owner || !open || !!busy} onClick={() => toggle(x)} aria-label={isDone ? `Mark step ${x.step_number} as not done` : `Mark step ${x.step_number} as done`} className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border ${isDone ? 'fs-grad-bg border-transparent text-bg' : 'border-line text-ink-3'} disabled:cursor-not-allowed`}>
                        {busy === `step-${x.id}` ? <Loader2 size={12} className="animate-spin" /> : x.locked ? <Lock size={12} /> : isDone ? <Check size={14} /> : <Circle size={0} />}
                      </button>
                      <div className="min-w-0 flex-1">
                        <p className={`font-medium ${isDone ? 'text-ink-2 line-through' : ''}`}>{x.step_number}. {x.title}{x.requires_power_off && <span className="ml-2 rounded-full border border-crit/40 px-2 py-px text-[11px] font-normal text-crit">power off</span>}</p>
                        <p className="mt-0.5 text-sm text-ink-2">{x.locked ? 'Locked by the server until both safety statements are recorded.' : x.instruction}</p>
                        {!x.locked && owner && open && !vis && <button onClick={() => visual(x)} disabled={!!busy} className="mt-2 inline-flex items-center gap-1 text-xs text-teal disabled:opacity-50">{busy === `vis-${x.id}` ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}Show a picture of this step</button>}
                        {vis && <div className="mt-2"><AuthImage src={vis.url} alt={`Illustration for step ${x.step_number}`} className="h-44 w-full max-w-xs rounded-xl border border-line" /><p className="mt-1 text-[11px] text-ink-3">AI-generated illustration, not a photo of this appliance.</p></div>}
                      </div>
                    </div>
                  </li>)
              })}
            </ol>
          </section>

          {owner && open && (
            <section aria-labelledby="fin-h" className="card card-pad">
              <h2 id="fin-h" className={`${h2} mb-4`}><span className={ico}><FileText size={16} /></span>Finish and create the service report</h2>
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Outcome">
                {([['resolved', 'Fixed'], ['not_resolved', 'Not fixed'], ['escalated', 'Escalated']] as const).map(([v, l]) => <button key={v} role="radio" aria-checked={outcome === v} onClick={() => setOutcome(v)} className={`rounded-xl border px-4 py-1.5 text-sm font-medium transition-colors ${outcome === v ? 'border-teal/70 bg-teal/12 text-ink' : 'border-line-2 text-ink-2 hover:text-ink'}`}>{l}</button>)}
              </div>
              {outcome === 'resolved' && <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-[var(--color-accent)]" checked={ftf === true} onChange={e => setFtf(e.target.checked)} />Fixed on this first visit</label>}
              <div className="mt-3 flex items-center gap-1" role="radiogroup" aria-label="Rate the guidance">
                <span className="mr-2 text-sm text-ink-2">Rate the guidance</span>
                {[1, 2, 3, 4, 5].map(n => <button key={n} role="radio" aria-checked={rating === n} aria-label={`${n} stars`} onClick={() => setRating(n)} className={`h-8 w-8 rounded-full text-sm ${rating >= n ? 'fs-amber-bg text-bg' : 'border border-line text-ink-3'}`}>{n}</button>)}
              </div>
              <label className="sr-only" htmlFor="notes">Notes</label>
              <textarea id="notes" value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Notes for the report (parts used, what you found)" className="field mt-3 text-sm" />
              <button onClick={report} disabled={!!busy} className="btn btn-primary mt-3">{busy === 'report' ? <Loader2 size={15} className="animate-spin" /> : <FileText size={15} />}Create report</button>
              <p className="mt-2 text-xs text-ink-3">The report lists only steps you marked done. Steps not done are shown as not performed.</p>
            </section>
          )}
        </div>
      </div>
      <CameraModal open={camera} onClose={() => setCamera(false)} onUse={addPhoto} />
    </div>
  )
}
