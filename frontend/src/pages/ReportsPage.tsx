import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Check, ChevronLeft, ChevronRight, Circle, Copy, Download, ExternalLink, FileText, Loader2, Printer, QrCode, Send } from 'lucide-react'
import { jobSummary, whatsappLink } from '../utils/jobSummary'
import { when } from '../utils/when'
import { EmptyState, ErrorState, PageHeader, Skeleton, StatusPill } from '../components/common/ui'
import { apiBase } from '../services/api'
import { historyService, receiptService, sessionService, type CustomerReceiptResponse } from '../services'
import { useAsync } from '../hooks/useAsync'

export function ReportsList() {
  const { data, loading, error, retry } = useAsync(() => historyService.reports(), [])
  return (
    <div className="page page-mid">
      <PageHeader eyebrow="Workspace" title="Service reports" subtitle="Generated from finished sessions, using only recorded data." />
      {loading && <div className="space-y-3">{[0, 1, 2].map(i => <Skeleton key={i} className="h-20" />)}</div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && data.items.length === 0 && <EmptyState icon={<FileText size={22} />} title="No reports yet" hint="Finish a repair session to create its service report." action={<Link to="/repairs" className="btn btn-primary">View open repairs</Link>} />}
      {data && data.items.length > 0 && (
        <ul className="card divide-y divide-line/70 overflow-hidden">
          {data.items.map(r => (
            <li key={r.id}><Link to={`/reports/${r.id}`} className="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-2/50">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-3 text-teal"><FileText size={18} /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{r.title}</p>
                <p className="mt-0.5 truncate text-xs text-ink-3"><span className="num">{r.reference}</span> · {r.appliance}{r.technician ? ` · ${r.technician}` : ''}</p>
              </div>
              <span className="hidden text-xs text-ink-3 sm:block">{when(r.created_at)}</span>
              <StatusPill status={r.resolution_status} />
              <ChevronRight size={16} className="text-ink-3 transition-transform group-hover:translate-x-0.5" />
            </Link></li>
          ))}
        </ul>
      )}
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
  const [copied, setCopied] = useState(false)
  const [receipt, setReceipt] = useState<CustomerReceiptResponse | null>(null)
  const [receiptBusy, setReceiptBusy] = useState(false)
  const createReceipt = async () => {
    if (!data) return
    setReceiptBusy(true); setErr(null)
    try { setReceipt(await receiptService.create(data.session_id)) } catch (e) { setErr((e as Error).message) } finally { setReceiptBusy(false) }
  }
  // Send the customer a plain summary of the visit: the phone's share sheet where there is one, WhatsApp otherwise.
  const share = async () => {
    if (!data) return
    const text = jobSummary(data)
    const nav = navigator as Navigator & { share?: (d: { title?: string; text?: string }) => Promise<void> }
    if (nav.share && /Android|iPhone|iPad/i.test(navigator.userAgent)) { try { await nav.share({ title: `Service report ${data.reference}`, text }); return } catch { /* cancelled */ return } }
    window.open(whatsappLink(text), '_blank', 'noopener')
  }
  const copy = async () => { if (!data) return; try { await navigator.clipboard.writeText(jobSummary(data)); setCopied(true); setTimeout(() => setCopied(false), 1800) } catch { setErr('Could not copy. Select the text and copy it instead.') } }
  const sec = 'border-t border-line py-5'
  const h2 = 'section-label mb-2'
  const d = data?.data
  return (
    <div className="page page-mid">
      <Link to="/reports" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-2 hover:text-ink print:hidden"><ChevronLeft size={16} />All reports</Link>
      {loading && <div className="space-y-3"><Skeleton className="h-10" /><Skeleton className="h-40" /></div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && d && (<>
        <PageHeader title={`Report ${data.reference}`} subtitle={`${d.session.appliance} · ${new Date(data.created_at).toLocaleDateString()} · ${d.session.technician ?? ''}`}
          eyebrow="Service report" right={<div className="flex flex-wrap items-center gap-2 print:hidden"><button onClick={() => void createReceipt()} disabled={receiptBusy} className="btn" title="Create bilingual customer safety receipt with QR code">{receiptBusy ? <Loader2 size={15} className="animate-spin" /> : <QrCode size={15} />}Safety Receipt QR</button><button onClick={() => void share()} className="btn" title="Send a short summary of this visit to the customer"><Send size={15} />Send to customer</button><button onClick={() => void copy()} className="btn" aria-live="polite">{copied ? <Check size={15} className="text-accent" /> : <Copy size={15} />}{copied ? 'Copied' : 'Copy summary'}</button><button onClick={() => window.print()} className="btn"><Printer size={15} />Print</button><button onClick={() => void download()} disabled={busy} className="btn btn-primary">{busy ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}Download PDF</button></div>} />
        {receipt && (
          <div className="card card-pad mb-4 flex flex-wrap items-center gap-4 border-accent/35 bg-accent/[0.04] print:hidden">
            <img src={`${apiBase}${receipt.qr_url}`} alt="Customer safety receipt QR code" className="h-24 w-24 rounded-lg border border-line bg-white p-1" />
            <div className="min-w-0 flex-1 space-y-1 text-sm">
              <p className="font-semibold text-ink">Customer Safety Receipt (Hindi / English)</p>
              <p className="text-xs text-ink-2">Shareable safety &amp; checks summary with zero customer personal data.</p>
              <Link to={`/receipt/${receipt.token}`} className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline">
                Open /receipt/{receipt.token.slice(0, 12)}… <ExternalLink size={12} />
              </Link>
            </div>
          </div>
        )}
        {err && <p role="alert" className="mb-4 rounded-xl border border-crit/40 bg-crit/10 px-4 py-2.5 text-sm text-crit">{err}</p>}
        <div className="card card-pad">
        <StatusPill status={data.resolution_status} />
        {d.demo && <p role="note" className="mt-3 rounded-xl border border-warn/35 bg-warn/[0.06] px-4 py-2.5 text-[13px] text-ink-2"><b>Demo scenario report.</b> The diagnosis and steps came from scripted sample content, not live AI. Safety statements and steps performed are real records from this session.</p>}
        <section className="mt-4 pb-5 pt-2"><h2 className={h2}>Customer issue</h2><p>{d.customer_issue || 'Not recorded'}</p></section>
        <section className={sec}><h2 className={h2}>Diagnosis</h2>{d.diagnosis ? <><p>{d.diagnosis.problem_summary}</p><ul className="mt-2 list-disc pl-5 text-sm">{d.diagnosis.faults.map(f => <li key={f.fault}>{f.fault} ({Math.round(f.confidence * 100)}% {d.demo ? 'sample value' : 'AI estimate'})</li>)}</ul><p className="mt-1 text-xs text-ink-3">{d.diagnosis.note}</p></> : <p className="text-ink-2">No diagnosis was run.</p>}</section>
        <section className={sec}><h2 className={h2}>Steps performed</h2>{d.steps_performed.length ? <ol className="list-decimal space-y-1 pl-5">{d.steps_performed.map(s => <li key={s.step_number}>{s.title}</li>)}</ol> : <p className="text-ink-2">None marked done.</p>}
          {d.steps_not_performed.length > 0 && <><h3 className="mb-1 mt-3 text-xs font-semibold text-ink-3">Not performed</h3><ul className="list-disc pl-5 text-sm text-ink-2">{d.steps_not_performed.map(s => <li key={s.step_number}>{s.title}</li>)}</ul></>}</section>
        <section className={sec}><h2 className={h2}>Parts identified</h2>{d.parts_identified.length ? <ul className="list-disc pl-5">{d.parts_identified.map((p, i) => <li key={i}>{p.name}</li>)}</ul> : <p className="text-ink-2">None.</p>}</section>
        <section className={sec}><h2 className={h2}>Recorded safety statements</h2>
          <ul className="space-y-1.5 text-sm">
            {([[d.safety.final_state.power_off_confirmed, 'Technician stated power was switched off'], [d.safety.final_state.tester_checked, 'Technician stated tester showed no live line']] as const).map(([on, label]) =>
              <li key={label} className="flex items-center gap-2">{on ? <Check size={15} className="text-ok" aria-label="Recorded" /> : <Circle size={13} className="text-ink-3" aria-label="Not recorded" />}{label}</li>)}
            <li className="text-ink-2">Unsafe attempts blocked by the server: <span className="num">{d.safety.blocked_attempts}</span></li></ul>
          <p className="mt-2 text-xs text-ink-3">{d.safety.disclaimer}</p></section>
        <section className={sec}><h2 className={h2}>Resolution</h2><p>{({ resolved: 'Fixed', not_resolved: 'Not fixed', escalated: 'Escalated to a senior technician' } as Record<string, string>)[d.resolution.outcome] ?? d.resolution.outcome}{d.resolution.first_time_fix ? ', on the first visit' : ''}</p>{d.resolution.notes && <p className="mt-1 text-ink-2">{d.resolution.notes}</p>}</section>
        <section className={sec}><h2 className={h2}>Technician feedback</h2><p>{d.feedback ? `Rated ${d.feedback.rating}/5` : 'No feedback given.'}</p></section>
        </div>
      </>)}
    </div>
  )
}
