import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Download, FileText, Loader2, Printer } from 'lucide-react'
import { EmptyState, ErrorState, PageHeader, Skeleton, StatusPill } from '../components/common/ui'
import { historyService, sessionService } from '../services'
import { useAsync } from '../hooks/useAsync'

export function ReportsList() {
  const { data, loading, error, retry } = useAsync(() => historyService.reports(), [])
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 md:px-8">
      <PageHeader eyebrow="Workspace" title="Service Reports" subtitle="Generated from finished sessions, using only recorded data." />
      {loading && <div className="space-y-3">{[0, 1, 2].map(i => <Skeleton key={i} className="h-20" />)}</div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && data.items.length === 0 && <EmptyState icon={<FileText size={22} />} title="No reports yet" hint="Finish a repair session to create its service report." />}
      <ul className="space-y-2.5">
        {data?.items.map(r => (
          <li key={r.id}><Link to={`/reports/${r.id}`} className="card card-hover flex items-center gap-4 px-5 py-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-surface-3 text-teal"><FileText size={19} /></span>
            <div className="min-w-0 flex-1"><p className="font-semibold">{r.reference} <span className="font-normal text-ink-3">· {r.appliance}</span></p><p className="truncate text-sm text-ink-2">{r.title}</p></div><StatusPill status={r.resolution_status} /><ChevronRight size={16} className="text-ink-3" />
          </Link></li>
        ))}
      </ul>
    </div>
  )
}

export function ReportDetailPage() {
  const { id = '' } = useParams()
  const { data, loading, error, retry } = useAsync(() => historyService.report(id), [id])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const download = async () => {
    if (!data) return
    setBusy(true); setErr(null)
    try { await sessionService.downloadPdf(data.session_id, data.session_reference) } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const sec = 'border-t border-line py-5'
  const h2 = 'section-label mb-2'
  const d = data?.data
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 md:px-8">
      <Link to="/reports" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-2 hover:text-ink print:hidden"><ChevronLeft size={16} />All reports</Link>
      {loading && <div className="space-y-3"><Skeleton className="h-10" /><Skeleton className="h-40" /></div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && d && (<>
        <PageHeader title={`Report ${data.reference}`} subtitle={`${d.session.appliance} · ${new Date(data.created_at).toLocaleDateString()} · ${d.session.technician ?? ''}`}
          eyebrow="Service report" right={<div className="flex items-center gap-2 print:hidden"><button onClick={() => window.print()} className="btn"><Printer size={15} />Print</button><button onClick={() => void download()} disabled={busy} className="btn btn-primary">{busy ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}Download PDF</button></div>} />
        {err && <p role="alert" className="mb-4 rounded-xl border border-crit/40 bg-crit/10 px-4 py-2.5 text-sm text-crit">{err}</p>}
        <div className="card card-pad">
        <StatusPill status={data.resolution_status} />
        {d.demo && <p role="note" className="mt-3 rounded-2xl border border-warn/50 bg-warn/10 px-4 py-3 text-sm text-warn"><b>Demo scenario report.</b> The diagnosis and steps came from scripted sample content, not live AI. Safety statements and steps performed are real records from this session.</p>}
        <section className="mt-4 pb-5 pt-2"><h2 className={h2}>Customer issue</h2><p>{d.customer_issue || 'Not recorded'}</p></section>
        <section className={sec}><h2 className={h2}>Diagnosis</h2>{d.diagnosis ? <><p>{d.diagnosis.problem_summary}</p><ul className="mt-2 list-disc pl-5 text-sm">{d.diagnosis.faults.map(f => <li key={f.fault}>{f.fault} ({Math.round(f.confidence * 100)}% {d.demo ? 'sample value' : 'AI estimate'})</li>)}</ul><p className="mt-1 text-xs text-ink-3">{d.diagnosis.note}</p></> : <p className="text-ink-2">No diagnosis was run.</p>}</section>
        <section className={sec}><h2 className={h2}>Steps performed</h2>{d.steps_performed.length ? <ol className="list-decimal space-y-1 pl-5">{d.steps_performed.map(s => <li key={s.step_number}>{s.title}</li>)}</ol> : <p className="text-ink-2">None marked done.</p>}
          {d.steps_not_performed.length > 0 && <><h3 className="mb-1 mt-3 text-xs font-semibold text-ink-3">Not performed</h3><ul className="list-disc pl-5 text-sm text-ink-2">{d.steps_not_performed.map(s => <li key={s.step_number}>{s.title}</li>)}</ul></>}</section>
        <section className={sec}><h2 className={h2}>Parts identified</h2>{d.parts_identified.length ? <ul className="list-disc pl-5">{d.parts_identified.map((p, i) => <li key={i}>{p.name}</li>)}</ul> : <p className="text-ink-2">None.</p>}</section>
        <section className={sec}><h2 className={h2}>Recorded safety statements</h2>
          <ul className="space-y-1 text-sm"><li>{d.safety.final_state.power_off_confirmed ? '✓' : '○'} Technician stated power was switched off</li><li>{d.safety.final_state.tester_checked ? '✓' : '○'} Technician stated tester showed no live line</li><li>Blocked unsafe attempts: {d.safety.blocked_attempts}</li></ul>
          <p className="mt-2 text-xs text-ink-3">{d.safety.disclaimer}</p></section>
        <section className={sec}><h2 className={h2}>Resolution</h2><p className="capitalize">{d.resolution.outcome.replace('_', ' ')}{d.resolution.first_time_fix ? ', fixed on first visit' : ''}</p>{d.resolution.notes && <p className="mt-1 text-ink-2">{d.resolution.notes}</p>}</section>
        <section className={sec}><h2 className={h2}>Technician feedback</h2><p>{d.feedback ? `Rated ${d.feedback.rating}/5` : 'No feedback given.'}</p></section>
        </div>
      </>)}
    </div>
  )
}
