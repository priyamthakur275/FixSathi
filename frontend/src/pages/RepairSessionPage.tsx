import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Camera, Check, ChevronLeft, ChevronRight, Circle, Cpu, Download, ExternalLink, FileText, HandHelping, ImagePlus, Loader2, Lock, MessageSquare, QrCode, ScanSearch, ShieldCheck, Sparkles, Star, Stethoscope, Wand2 } from 'lucide-react'
import { CameraModal } from '../components/camera/CameraModal'
import { SafetyPanel } from '../components/repair/SafetyPanel'
import { RepairProgress } from '../components/repair/RepairProgress'
import { DiagnosisCard } from '../components/repair/DiagnosisCard'
import { ChallengerCard } from '../components/repair/ChallengerCard'
import { ExpectedReadingsCard } from '../components/repair/ExpectedReadingsCard'
import { NameplateCard } from '../components/repair/NameplateCard'
import { PartCard } from '../components/repair/PartCard'
import { AuthImage } from '../components/common/AuthImage'
import { ErrorState, Skeleton, StatusPill } from '../components/common/ui'
import { SourceList } from '../components/common/SourceList'
import { fileService, receiptService, repairService, sessionService, type CustomerReceiptResponse } from '../services'
import { apiBase, type ApiError } from '../services/api'
import { DocChip } from '../components/composer/Composer'
import { openFile } from '../utils/openFile'
import { useAuth } from '../context/AuthContext'
import { useT } from '../i18n'
import type { Attachment, ComponentResult, Diagnosis, MediaItem, NameplateResponse, RepairSession, RepairStep, SafetyState, SimilarResult } from '../types'

const CLOSED = ['completed', 'cancelled']
const btn = 'btn'
const h2 = 'flex items-center gap-2.5 text-[15px] font-semibold tracking-tight'
const ico = 'flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface-2 text-accent'

const sourceLine = (why: string) => why.replace(/\s*\((verified_source|verified)\)\s*$/, ' · verified').replace(/\s*\(unverified\)\s*$/, ' · not yet verified')

export default function RepairSessionPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const t = useT()
  const nav = useNavigate()
  const { hash } = useLocation()
  const [s, setS] = useState<RepairSession | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [media, setMedia] = useState<MediaItem[]>([])
  const [diag, setDiag] = useState<Diagnosis | null>(null)
  const [steps, setSteps] = useState<RepairStep[]>([])
  const [safety, setSafety] = useState<SafetyState | null>(null)
  const [comp, setComp] = useState<ComponentResult | null>(null)
  const [nameplateRes, setNameplateRes] = useState<NameplateResponse | null>(null)
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
  const [causeRight, setCauseRight] = useState<boolean | null>(null)
  const [receipt, setReceipt] = useState<CustomerReceiptResponse | null>(null)
  const [activeStage, setActiveStage] = useState<number>(hash === '#safety' ? 2 : 0)
  const [stagePicked, setStagePicked] = useState(hash === '#safety')

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

  const ready = !!s && !!safety
  useEffect(() => {
    if (ready && hash === '#safety') {
      setActiveStage(2)
      setStagePicked(true)
      document.getElementById('safety')?.scrollIntoView({ block: 'start' })
    }
  }, [ready, hash])

  const isPhoto = (m: MediaItem) => m.kind !== 'generated' && m.kind !== 'document' && m.mime_type.startsWith('image/')
  const photos = media.filter(isPhoto)
  const docs = media.filter(m => m.kind === 'document')
  const done = steps.filter(x => x.status === 'completed').length

  // Auto-select the first incomplete stage once data loads unless the user picked one explicitly.
  useEffect(() => {
    if (!s || stagePicked) return
    const stageDone = [
      !!s.issue_description || photos.length > 0,
      !!diag,
      !!safety?.unlocked || !!s.report_id,
      steps.length > 0 && done === steps.length,
      !!s.report_id,
    ]
    const firstOpen = stageDone.findIndex(v => !v)
    setActiveStage(firstOpen === -1 ? 4 : firstOpen)
  }, [s, diag, safety?.unlocked, steps.length, done, photos.length, stagePicked])

  const selectStage = (idx: number) => {
    setStagePicked(true)
    setActiveStage(Math.max(0, Math.min(4, idx)))
  }

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
  const diagnose = () => run('diagnose', async () => {
    const d = await repairService.diagnose(id, media.filter(isPhoto).slice(-3).map(m => m.id))
    setDiag(d)
    setSafety(await repairService.safety(id))
    await refreshSession()
  })
  const ackChallenger = () => run('challenger-ack', async () => { setDiag(await repairService.acknowledgeChallenger(id)) })
  const genSteps = () => run('steps', async () => { setSteps(await repairService.generateSteps(id)); await refreshSession() })
  const setSafe = (p: boolean, tester: boolean) => run('safety', async () => { setSafety(await repairService.confirmSafety(id, p, tester)); setSteps(await repairService.steps(id)) })
  const toggle = (x: RepairStep) => run(`step-${x.id}`, async () => {
    const u = x.status === 'completed' ? await repairService.reopenStep(id, x.id) : await repairService.completeStep(id, x.id)
    setSteps(st => st.map(y => y.id === u.id ? u : y))
  })
  const visual = (x: RepairStep) => run(`vis-${x.id}`, async () => { const m = await repairService.stepVisual(id, x.id); setMedia(v => v.some(y => y.id === m.id) ? v : [...v, m]); setSteps(st => st.map(y => y.id === x.id ? { ...y, visual_media_id: m.id } : y)) })
  const identify = (m: MediaItem) => run(`id-${m.id}`, async () => setComp(await repairService.identify(id, m.id)))
  const readNameplate = (m: MediaItem) => run(`np-${m.id}`, async () => {
    const res = await repairService.readNameplate(id, m.id)
    setNameplateRes(res)
    if (res.status === 'ok') {
      await refreshSession()
      repairService.similar(id).then(setSimilar).catch(() => undefined)
    }
  })
  const saveNameplate = (patch: Parameters<typeof repairService.updateNameplate>[1]) => run('np-save', async () => {
    const res = await repairService.updateNameplate(id, patch)
    setNameplateRes(res)
    await refreshSession()
    repairService.similar(id).then(setSimilar).catch(() => undefined)
  })
  const trySampleNameplate = () => run('np-sample', async () => {
    const blob = await fileService.sampleNameplate()
    const m = await fileService.upload(id, blob, 'upload', 'sample_nameplate.png')
    setMedia(x => [...x, m])
    const res = await repairService.readNameplate(id, m.id)
    setNameplateRes(res)
    if (res.status === 'ok') {
      await refreshSession()
      repairService.similar(id).then(setSimilar).catch(() => undefined)
    }
  })
  const escalate = () => run('esc', async () => { await repairService.escalate(id, escReason); setShowEsc(false); setEscReason(''); await refreshSession(); setMsg({ kind: 'info', text: 'Senior technician support requested. A manager will see it under Senior support.' }) })
  const report = () => run('report', async () => {
    if (rating) await repairService.feedback(id, rating, causeRight)
    const r = await repairService.report(id, outcome, outcome === 'resolved' ? ftf : null, notes); nav(`/reports/${r.id}`)
  })
  const makeReceipt = () => run('receipt', async () => { setReceipt(await receiptService.create(id)) })

  if (loadErr) return <div className="mx-auto max-w-3xl px-4 py-10"><ErrorState message={loadErr} onRetry={() => void load()} /></div>
  if (!s) return <div className="mx-auto max-w-6xl space-y-4 px-4 py-8 md:px-8"><Skeleton className="h-12 w-1/2" /><Skeleton className="h-20" /><Skeleton className="h-64" /></div>

  const pct = steps.length ? Math.round(done / steps.length * 100) : 0
  const stages = [
    { label: t('stage.describe'), done: !!s.issue_description || photos.length > 0 },
    { label: t('stage.diagnose'), done: !!diag },
    { label: t('stage.isolate'), done: !!safety?.unlocked || !!s.report_id },
    { label: t('stage.repair'), done: steps.length > 0 && done === steps.length },
    { label: t('stage.report'), done: !!s.report_id },
  ]
  const visStage = (idx: number) => (activeStage === idx ? 'block' : 'hidden lg:block')

  return (
    <div className="page !pt-0 lg:!pt-6">
      {/* Sticky mobile safety bar: always visible on phones so power state is never buried below the fold */}
      {safety && (
        <div role="region" aria-label="Power safety status"
          className={`sticky top-0 z-20 -mx-4 mb-4 flex items-center justify-between gap-3 border-b-2 px-4 py-2.5 lg:hidden ${safety.unlocked ? 'border-ok/60 bg-surface text-ok' : 'border-crit/60 bg-surface text-crit'}`}>
          <div className="flex min-w-0 items-center gap-2 text-xs font-semibold">
            {safety.unlocked ? <ShieldCheck size={16} className="shrink-0" aria-hidden /> : <Lock size={16} className="shrink-0" aria-hidden />}
            <span className="truncate">{safety.unlocked ? 'Isolated · Power steps unlocked' : 'Live · Power steps locked'}</span>
          </div>
          {!safety.unlocked && open && (
            <button type="button" onClick={() => selectStage(2)} className="btn btn-sm !min-h-[44px] border-crit/50 bg-crit/12 px-3 text-xs font-semibold text-crit">
              Isolate now
            </button>
          )}
        </div>
      )}

      <Link to={`/chat/${id}`} className="mb-4 inline-flex min-h-[44px] items-center gap-1 text-sm text-ink-2 transition-colors hover:text-ink"><ChevronLeft size={16} />Back to chat</Link>
      {s.demo && <div role="note" className="mb-4 rounded-xl border border-warn/35 bg-warn/[0.06] px-4 py-2.5 text-[13px] leading-relaxed text-ink-2"><b className="font-semibold text-warn">Demo: scripted sample, not live AI.</b> Diagnosis, steps and replies here are scripted sample content. The safety lock, logging and report are the real server code.</div>}

      <header className="card mb-6 overflow-hidden">
        <div className="card-pad">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="flex flex-wrap items-center gap-2 text-[13px] text-ink-2">
                <span className="font-semibold text-teal">{s.appliance_label}</span>
                <span className="num rounded-md border border-line bg-surface-2 px-1.5 py-px text-[12px] text-ink-3" title="Session reference">{s.reference}</span>
                <StatusPill status={s.status} />
                {s.technician_name && !owner && <span className="text-xs text-ink-2">Technician: {s.technician_name}</span>}
              </p>
              <h1 className="font-display mt-2 text-[22px] leading-snug md:text-[28px]">{s.title}</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className={btn} onClick={() => nav(`/chat/${id}`)}><MessageSquare size={16} />Chat</button>
              <button className={btn} disabled={busy === 'pdf'} onClick={() => run('pdf', () => sessionService.downloadPdf(id, s.reference))}>{busy === 'pdf' ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}PDF</button>
              {owner && open && s.status !== 'escalated' && <button onClick={() => setShowEsc(v => !v)} className="btn btn-warn"><HandHelping size={16} />Ask a senior technician</button>}
              {s.report_id && <Link to={`/reports/${s.report_id}`} className={btn}><FileText size={16} />Report</Link>}
            </div>
          </div>
          <RepairProgress isolateIndex={2} stages={stages} activeIndex={activeStage} onSelect={selectStage} />
        </div>
      </header>

      {showEsc && (
        <div className="mb-6 flex flex-col gap-2 rounded-2xl border border-warn/30 bg-warn/5 p-4 sm:flex-row">
          <label className="sr-only" htmlFor="esc">Reason</label>
          <input id="esc" value={escReason} onChange={e => setEscReason(e.target.value)} placeholder="Why do you need a senior? e.g. burnt smell in canopy" className="field flex-1 !py-2.5 text-sm" />
          <button disabled={escReason.trim().length < 3 || busy === 'esc'} onClick={escalate} className="btn !border-0 !bg-warn font-semibold !text-white">Send request</button>
        </div>
      )}
      {msg && <p role={msg.kind === 'error' ? 'alert' : 'status'} className={`mb-6 rounded-2xl border px-4 py-3 text-sm ${msg.kind === 'error' ? 'border-crit/40 bg-crit/10 text-crit' : 'border-accent/40 bg-accent/10 text-ink'}`}>{msg.text}</p>}

      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="min-w-0 space-y-6">
          {/* Stage 0: Describe */}
          <section aria-labelledby="insp-h" className={`card card-pad ${visStage(0)}`}>
            <h2 id="insp-h" className={`${h2} mb-4`}><span className={ico}><Camera size={16} /></span>1. Describe &amp; visual inspection</h2>
            {s.issue_description && <p className="mb-4 rounded-xl border border-line bg-surface-2/50 px-3.5 py-2.5 text-sm text-ink-2"><strong className="font-semibold text-ink">Reported fault:</strong> {s.issue_description}</p>}
            {photos.length === 0 ? (
              <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line-2 bg-surface/40 px-6 py-10 text-center">
                <Camera className="text-ink-3" /><p className="text-sm text-ink-2">No photos yet. Show the appliance or nameplate with your camera.</p>
                {owner && open && (
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    <button onClick={() => setCamera(true)} className="btn btn-primary"><ImagePlus size={16} />Show me the appliance</button>
                    <button type="button" onClick={trySampleNameplate} disabled={!!busy} className="btn">
                      {busy === 'np-sample' ? <Loader2 size={15} className="animate-spin" /> : <Cpu size={15} />}
                      Try a sample nameplate
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  {photos.map(m => (
                    <div key={m.id} className="w-36">
                      <AuthImage src={m.url} alt="Appliance photo" className="h-32 w-36 rounded-2xl border border-line" box={comp?.media_id === m.id ? comp.box : null} label={comp?.media_id === m.id ? comp.component_name : null} />
                      {owner && open && (
                        <div className="mt-1.5 flex flex-col">
                          <button type="button" onClick={() => identify(m)} disabled={!!busy} className="inline-flex min-h-[44px] items-center gap-1 text-left text-xs font-medium text-accent disabled:opacity-50">{busy === `id-${m.id}` ? <Loader2 size={12} className="animate-spin" /> : <ScanSearch size={13} />}Identify component</button>
                          <button type="button" onClick={() => readNameplate(m)} disabled={!!busy} className="inline-flex min-h-[44px] items-center gap-1 text-left text-xs font-medium text-teal disabled:opacity-50">{busy === `np-${m.id}` ? <Loader2 size={12} className="animate-spin" /> : <Cpu size={13} />}Read nameplate / code</button>
                        </div>
                      )}
                    </div>
                  ))}
                  {owner && open && <button onClick={() => setCamera(true)} aria-label="Add another photo" className="flex h-32 w-32 items-center justify-center rounded-2xl border border-dashed border-line-2 text-ink-2 transition-colors hover:border-accent/60 hover:bg-surface-2 hover:text-accent"><ImagePlus /></button>}
                </div>
                {owner && open && (
                  <button type="button" onClick={trySampleNameplate} disabled={!!busy} className="btn btn-sm">
                    {busy === 'np-sample' ? <Loader2 size={13} className="animate-spin" /> : <Cpu size={13} />}
                    Try a sample nameplate
                  </button>
                )}
                {comp && <div className="rounded-2xl border border-accent/25 bg-accent/[0.05] p-3.5 text-sm"><p className="font-medium">{comp.found ? comp.component_name : 'Not identified'}</p><p className="text-ink-2">{comp.explanation}</p>{comp.uncertainty && <p className="mt-1 text-xs text-ink-3">{comp.uncertainty}</p>}<p className="mt-1 text-xs text-ink-3">{comp.note}</p></div>}
              </div>
            )}
            <NameplateCard
              initialNameplate={s.nameplate}
              response={nameplateRes}
              sessionAppliance={s.appliance_type}
              canEdit={owner && open}
              busy={busy === 'np-save' || (busy?.startsWith('np-') ?? false)}
              onSave={saveNameplate}
            />
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
            {busy === 'upload' && <p className="mt-3 flex items-center gap-2 text-xs text-ink-2"><Loader2 size={12} className="animate-spin text-accent" />Uploading...</p>}
          </section>

          {/* Stage 1: Diagnose */}
          {(() => {
            const np = nameplateRes?.extracted ?? s.nameplate
            const nameplateNeedsConfirm = !!np && !np.verified_by_technician && !!(np.model || np.brand || np.error_code)
            const lockedCount = steps.filter(x => x.locked).length
            const ch = diag?.challenger
            return (
          <section aria-labelledby="diag-h" className={`card card-pad ${visStage(1)}`}>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 id="diag-h" className={h2}><span className={ico}><Stethoscope size={16} /></span>2. Suspected faults</h2>
              {owner && open && (
                <button onClick={diagnose} disabled={!!busy || nameplateNeedsConfirm} className={btn}>
                  {busy === 'diagnose' ? <Loader2 size={15} className="animate-spin" /> : <Stethoscope size={15} />}
                  {diag ? 'Re-run diagnosis' : 'Run diagnosis'}
                </button>
              )}
            </div>
            {nameplateNeedsConfirm && owner && open && (
              <p role="note" className="mb-3 rounded-xl border border-warn/45 bg-warn/10 px-3.5 py-2.5 text-xs text-ink-2">
                Confirm the read model number under <strong className="font-semibold text-ink">Nameplate &amp; error display</strong> (<strong className="font-semibold text-ink">Confirm &amp; use model</strong>) before running diagnosis.
              </p>
            )}
            {!diag && <p className="text-sm text-ink-2">No diagnosis yet. Describe the issue in chat or add a photo, then run the diagnosis.</p>}
            {diag && (<>
              <p className="mb-2.5 text-sm text-ink-2">{diag.problem_summary}</p>
              <p className={`mb-3 inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${diag.knowledge_coverage === 'grounded' ? 'border-accent/40 text-accent' : 'border-warn/40 text-warn'}`}>
                {diag.knowledge_coverage === 'grounded' ? 'Backed by repair records' : diag.knowledge_coverage === 'partial' ? 'Partly backed by repair records' : 'No matching repair record: treat as unverified'}
              </p>
              {diag.confirmed_findings?.length > 0 && <p className="mb-3 text-sm"><span className="text-ink-2">Confirmed: </span>{diag.confirmed_findings.join('; ')}</p>}
              <div className={ch ? 'grid items-start gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]' : ''}>
                <ul className="space-y-3">
                  {diag.faults.map((f, idx) => <DiagnosisCard key={f.fault} fault={f} sources={diag.sources ?? []} index={idx} />)}
                </ul>
                {ch && (
                  <ChallengerCard
                    challenger={ch}
                    checkedAt={diag.challenger_checked_at}
                    canEdit={owner && open}
                    busy={busy === 'challenger-ack'}
                    onAcknowledge={ackChallenger}
                  />
                )}
              </div>
              {diag.follow_up_questions.length > 0 && <div className="mt-4 rounded-xl border border-line bg-surface-2/50 p-3.5 text-sm"><p className="mb-1.5 text-xs font-medium text-ink-3">Check next</p><ul className="space-y-1">{diag.follow_up_questions.map(q => <li key={q} className="flex gap-2"><span aria-hidden className="text-accent">?</span>{q}</li>)}</ul></div>}
              {diag.missing_information?.length > 0 && <div className="mt-3 text-sm"><p className="text-ink-2">Still unknown:</p><ul className="list-disc pl-5">{diag.missing_information.map(q => <li key={q}>{q}</li>)}</ul></div>}
              {(diag.required_tools?.length ?? 0) > 0 && <p className="mt-3 text-sm"><span className="text-ink-2">Tools needed:</span> {diag.required_tools!.join(', ')}</p>}
              {diag.sources?.length > 0 && <SourceList sources={diag.sources} />}
              {diag.requires_escalation && <p className="mt-3 rounded-xl border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">The AI recommends a senior technician for this fault.{diag.escalation_reason ? ` ${diag.escalation_reason}` : ''}</p>}
              <details className="mt-3 rounded-xl border border-line bg-surface-2/40 px-3.5 py-2.5 text-xs text-ink-2">
                <summary className="cursor-pointer font-semibold text-ink select-none">How this answer was made</summary>
                <dl className="mt-2.5 space-y-1.5">
                  {diag.model_identifier && (
                    <div className="flex flex-wrap justify-between gap-2"><dt className="text-ink-3">Diagnosis model</dt><dd className="font-mono text-ink">{diag.model_identifier}</dd></div>
                  )}
                  {np?.model_identifier && (
                    <div className="flex flex-wrap justify-between gap-2"><dt className="text-ink-3">Vision model</dt><dd className="font-mono text-ink">{np.model_identifier}</dd></div>
                  )}
                  {typeof diag.latency_ms === 'number' && (
                    <div className="flex flex-wrap justify-between gap-2"><dt className="text-ink-3">Latency</dt><dd className="num text-ink">{diag.latency_ms} ms</dd></div>
                  )}
                  <div className="flex flex-wrap justify-between gap-2">
                    <dt className="text-ink-3">Repair records retrieved</dt>
                    <dd className="num text-ink">{diag.sources?.length ?? 0}</dd>
                  </div>
                  {diag.sources && diag.sources.length > 0 && (
                    <div>
                      <dt className="text-ink-3">RAG sources</dt>
                      <dd className="mt-1 flex flex-wrap gap-1.5">
                        {diag.sources.map(src => (
                          <span key={src.record_id} className="rounded-md border border-line bg-surface px-2 py-0.5 font-mono text-[11px] text-ink-2">
                            {src.record_id} · {src.source_name}
                          </span>
                        ))}
                      </dd>
                    </div>
                  )}
                  {(lockedCount > 0 || safety) && (
                    <div className="flex flex-wrap justify-between gap-2">
                      <dt className="text-ink-3">Safety guardrail</dt>
                      <dd className="text-ink">
                        {lockedCount > 0
                          ? `Withheld ${lockedCount} power-sensitive step(s) until MCB off + tester confirmed`
                          : safety?.unlocked
                            ? 'Unlocked after MCB off + tester statements'
                            : 'Active (locks power-sensitive steps)'}
                      </dd>
                    </div>
                  )}
                  {ch && (
                    <>
                      <div className="flex flex-wrap justify-between gap-2">
                        <dt className="text-ink-3">Challenger model</dt>
                        <dd className="font-mono text-ink">{ch.model_identifier ?? 'Unavailable'}</dd>
                      </div>
                      <div className="flex flex-wrap justify-between gap-2">
                        <dt className="text-ink-3">Challenger verdict</dt>
                        <dd className="text-ink">
                          {ch.status === 'unavailable' ? 'Unavailable' : ch.agrees ? 'Agreed' : 'Disagreed'}
                          {typeof ch.latency_ms === 'number' ? ` (${ch.latency_ms} ms)` : ''}
                        </dd>
                      </div>
                    </>
                  )}
                </dl>
              </details>
              <p className="mt-3 text-xs text-ink-3">{diag.confidence_note}</p>
            </>)}
            <ExpectedReadingsCard appliance={s.appliance_type} />
          </section>
            )
          })()}

          {similar && similar.results.length > 0 && (
            <section aria-labelledby="sim-h" className={`card card-pad ${visStage(1)}`}>
              <h2 id="sim-h" className={`${h2} mb-3`} title={`Search: ${similar.mode}${similar.fallback_reason ? ` (${similar.fallback_reason})` : ''}`}><span className={ico}><FileText size={16} /></span>Related repairs and records</h2>
              <ul className="-mx-2 text-sm">{similar.results.map(r => (
                <li key={r.source_id} className="rounded-lg px-2 py-2.5 transition-colors hover:bg-surface-2/60">
                  {r.source_type === 'session' && r.report_id ? <Link className="font-medium hover:text-accent" to={`/reports/${r.report_id}`}>{r.reference}: {r.title}</Link> : <span className="font-medium first-letter:uppercase">{r.title.replace(/^[^:]*: /, '')}</span>}
                  {r.snippet && <p className="mt-0.5 text-ink-2">{r.snippet}</p>}
                  <p className="mt-0.5 truncate text-xs text-ink-3" title={r.why}>{r.source_type === 'session' ? 'Your earlier repair' : sourceLine(r.why)}</p>
                </li>
              ))}</ul>
            </section>
          )}
        </div>

        <div className="min-w-0 space-y-6">
          {/* Stage 2: Isolate (always visible on desktop right rail; step 3 on mobile) */}
          <div className={visStage(2)}>
            <SafetyPanel state={safety} busy={busy === 'safety'} canEdit={owner && open} onChange={setSafe} appliance={s?.appliance_type} />
          </div>

          {/* Stage 3: Repair */}
          {(() => {
            const challengerNeedsCheck = !!(diag?.challenger && diag.challenger.status === 'ok' && diag.challenger.agrees === false && !diag.challenger_checked_at)
            return (
          <section aria-labelledby="steps-h" className={`card card-pad ${visStage(3)}`}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 id="steps-h" className={`${h2} whitespace-nowrap`}><span className={ico}><Wand2 size={16} /></span>4. Repair guidance</h2>
              {owner && open && diag && done === 0 && <button onClick={genSteps} disabled={!!busy || challengerNeedsCheck} className={btn}>{busy === 'steps' ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />}{steps.length ? 'Regenerate' : 'Generate steps'}</button>}</div>
            {challengerNeedsCheck && (
              <div role="note" className="mb-4 rounded-xl border border-warn/45 bg-warn/10 p-3.5 text-sm text-ink-2">
                <p className="font-semibold text-ink">Challenger raised an objection</p>
                <p className="mt-1 text-xs">Review the Challenger card under <strong className="text-ink">2. Suspected faults</strong> and tap <strong className="text-ink">I checked this</strong> before repair steps are shown.</p>
                <button type="button" onClick={() => selectStage(1)} className="btn btn-sm mt-2.5 lg:hidden">Review Challenger objections</button>
              </div>
            )}
            {!challengerNeedsCheck && steps.length > 0 && <div className="mb-4 flex items-center gap-3">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Step progress"><div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: `${pct}%` }} /></div>
              <span className="num text-xs text-ink-3">{done} of {steps.length}</span>
            </div>}
            {!challengerNeedsCheck && steps.length === 0 && <p className="text-sm text-ink-2">{diag ? 'Generate steps from the diagnosis, or get them live by voice.' : 'Steps appear after a diagnosis.'}</p>}
            {!challengerNeedsCheck && <ol className="space-y-2.5">
              {steps.map(x => {
                const isDone = x.status === 'completed'
                const vis = x.visual_media_id ? media.find(m => m.id === x.visual_media_id) : undefined
                return (
                  <li key={x.id} className={`rounded-xl border p-4 transition-colors ${x.locked ? 'border-crit/40 bg-surface-2/40' : isDone ? 'border-accent/30 bg-accent/[0.04]' : 'border-line bg-bg/30'}`}>
                    <div className="flex items-start gap-3">
                      <button disabled={!owner || !open || !!busy} onClick={() => toggle(x)} aria-label={isDone ? `Mark step ${x.step_number} as not done` : `Mark step ${x.step_number} as done`} className={`mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border transition-colors ${isDone ? 'border-transparent bg-accent text-white' : x.locked ? 'border-crit/50 text-crit' : 'border-line-2 text-ink-3 hover:border-accent hover:text-accent'} disabled:cursor-not-allowed`}>
                        {busy === `step-${x.id}` ? <Loader2 size={15} className="animate-spin" /> : x.locked ? <Lock size={15} /> : isDone ? <Check size={16} /> : <Circle size={12} />}
                      </button>
                      <div className="min-w-0 flex-1">
                        <p className={`font-medium ${isDone ? 'text-ink-2 line-through' : ''}`}>{x.step_number}. {x.title}{x.requires_power_off && !x.locked && <span className="ml-2 rounded-full border border-ok/40 bg-ok/10 px-2 py-px text-[12px] font-normal text-ok">isolated</span>}</p>
                        {x.locked ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-xs font-medium text-crit/90">Withheld until you confirm: MCB off + tester reading</p>
                            <button type="button" onClick={() => selectStage(2)} className="inline-flex min-h-[44px] items-center gap-1.5 text-sm font-medium text-crit hover:underline">
                              <Lock size={14} aria-hidden />Isolate the power to unlock
                            </button>
                          </div>
                        ) : (
                          <>
                            <p className="mt-1 text-sm leading-relaxed text-ink-2">{x.instruction}</p>
                            <PartCard title={x.title} instruction={x.instruction} appliance={s.appliance_type} />
                            {owner && open && !vis && <button onClick={() => visual(x)} disabled={!!busy} className="mt-2 inline-flex min-h-[44px] items-center gap-1.5 text-xs font-medium text-accent disabled:opacity-50">{busy === `vis-${x.id}` ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={13} />}Show an AI step illustration</button>}
                            {vis && <div className="mt-2"><AuthImage src={vis.url} alt={`Illustration for step ${x.step_number}`} className="h-44 w-full max-w-xs rounded-xl border border-line" /><p className="mt-1 text-[12px] text-ink-3">AI-generated illustration, not a photo of this appliance.</p></div>}
                          </>
                        )}
                      </div>
                    </div>
                  </li>)
              })}
            </ol>}
          </section>
            )
          })()}

          {/* Stage 4: Report */}
          {owner && open && (
            <section aria-labelledby="fin-h" className={`card card-pad ${visStage(4)}`}>
              <h2 id="fin-h" className={`${h2} mb-4`}><span className={ico}><FileText size={16} /></span>5. Finish and create the service report</h2>
              <div className="inline-flex rounded-xl border border-line bg-bg/40 p-1" role="radiogroup" aria-label="Outcome">
                {([['resolved', 'Fixed'], ['not_resolved', 'Not fixed'], ['escalated', 'Escalated']] as const).map(([v, l]) => <button key={v} role="radio" aria-checked={outcome === v} onClick={() => setOutcome(v)} className={`min-h-[44px] rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${outcome === v ? 'bg-surface text-ink shadow-[var(--shadow-card)] ring-1 ring-line-2' : 'text-ink-2 hover:text-ink'}`}>{l}</button>)}
              </div>
              {outcome === 'resolved' && <label className="mt-3 flex min-h-[44px] items-center gap-2.5 text-sm"><input type="checkbox" className="h-5 w-5 accent-[var(--color-accent)]" checked={ftf === true} onChange={e => setFtf(e.target.checked)} />Fixed on this first visit</label>}
              <p className="mt-4 text-sm text-ink-2" id="rate-l">Rate the guidance</p>
              <div className="mt-1 flex items-center gap-1" role="radiogroup" aria-labelledby="rate-l">
                {[1, 2, 3, 4, 5].map(n => <button key={n} role="radio" aria-checked={rating === n} aria-label={`${n} stars`} onClick={() => setRating(n)} className={`flex h-11 w-11 items-center justify-center rounded-lg transition-colors hover:bg-surface-2 ${rating >= n ? 'text-amber' : 'text-ink-3'}`}><Star size={20} className={rating >= n ? 'fill-current' : ''} aria-hidden /></button>)}
              </div>
              {diag && rating > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-2" role="radiogroup" aria-label="Was the likely cause right?">
                  <span className="mr-1 text-sm text-ink-2">Was “{diag.faults[0]?.fault ?? 'the likely cause'}” right?</span>
                  {([[true, 'Yes'], [false, 'No'], [null, 'Not sure']] as const).map(([v, l]) => <button key={l} role="radio" aria-checked={causeRight === v} onClick={() => setCauseRight(v)} className={`min-h-[44px] rounded-lg border px-3.5 py-1.5 text-sm transition-colors ${causeRight === v ? 'border-line-2 bg-surface text-ink shadow-[var(--shadow-card)]' : 'border-line text-ink-2 hover:text-ink'}`}>{l}</button>)}
                </div>
              )}
              <label className="sr-only" htmlFor="notes">Notes</label>
              <textarea id="notes" value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Notes for the report (parts used, what you found)" className="field mt-3 text-sm" />
              <div className="mt-3 flex flex-wrap gap-2">
                <button onClick={report} disabled={!!busy} className="btn btn-primary">{busy === 'report' ? <Loader2 size={15} className="animate-spin" /> : <FileText size={15} />}Create report</button>
                <button type="button" onClick={makeReceipt} disabled={!!busy} className="btn">{busy === 'receipt' ? <Loader2 size={15} className="animate-spin" /> : <QrCode size={15} />}Customer Safety Receipt</button>
              </div>
              {receipt && (
                <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-accent/35 bg-accent/[0.04] p-3">
                  <img src={`${apiBase}${receipt.qr_url}`} alt="Customer safety receipt QR code" className="h-20 w-20 rounded-lg border border-line bg-white p-1" />
                  <div className="min-w-0 flex-1 text-xs">
                    <p className="font-semibold text-ink">Safety Receipt ready (Hindi / English)</p>
                    <p className="mt-0.5 text-ink-2">No customer personal data stored.</p>
                    <Link to={`/receipt/${receipt.token}`} className="mt-1 inline-flex items-center gap-1 font-medium text-accent hover:underline">
                      Open receipt <ExternalLink size={12} />
                    </Link>
                  </div>
                </div>
              )}
              <p className="mt-2 text-xs text-ink-3">The report lists only steps you marked done. Steps not done are shown as not performed.</p>
            </section>
          )}
        </div>
      </div>

      {/* Mobile guided step navigation footer */}
      <nav aria-label="Guided repair steps" className="mt-6 flex items-center justify-between gap-3 border-t border-line pt-4 lg:hidden">
        <button type="button" onClick={() => selectStage(activeStage - 1)} disabled={activeStage === 0} className="btn flex-1">
          <ChevronLeft size={16} />Previous
        </button>
        <button type="button" onClick={() => selectStage(activeStage + 1)} disabled={activeStage === 4} className="btn btn-primary flex-1">
          {activeStage < 4 ? `Next: ${stages[activeStage + 1].label}` : 'Report'}<ChevronRight size={16} />
        </button>
      </nav>

      <CameraModal open={camera} onClose={() => setCamera(false)} onUse={addPhoto} />
    </div>
  )
}
