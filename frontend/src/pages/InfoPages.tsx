import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bookmark, ChevronRight, HandHelping, MessageSquareText } from 'lucide-react'
import { when } from '../utils/when'
import { appliances } from '../constants/prompts'
import { EmptyState, ErrorState, PageHeader, Skeleton, StatusPill } from '../components/common/ui'
import { historyService } from '../services'
import { useAsync } from '../hooks/useAsync'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'

export function SavedDiagnoses() {
  const { data, loading, error, retry } = useAsync(() => historyService.diagnoses(), [])
  return (
    <div className="page page-mid">
      <PageHeader eyebrow="Workspace" title="Saved diagnoses" subtitle="AI diagnoses from your repair sessions." />
      {loading && <Skeleton className="h-40" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && data.length === 0 && <EmptyState icon={<Bookmark size={22} />} title="No diagnoses yet" hint="Run a diagnosis inside a repair session." action={<Link to="/" className="btn btn-primary">Start a repair</Link>} />}
      {data && data.length > 0 && (
        <ul className="card divide-y divide-line/70 overflow-hidden">
          {data.map(d => {
            const pct = d.top_fault ? Math.round(d.top_fault.confidence * 100) : null
            return (
              <li key={d.id}><Link to={`/session/${d.session_id}`} className="group flex items-center gap-5 px-5 py-4 transition-colors hover:bg-surface-2/50">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{d.top_fault?.fault ?? d.problem_summary}</p>
                  <p className="mt-0.5 truncate text-sm text-ink-2">{d.problem_summary}</p>
                  <p className="mt-1 truncate text-xs text-ink-3"><span className="num">{d.reference}</span> · {when(d.created_at)}</p>
                </div>
                {pct !== null && <div className="hidden w-28 shrink-0 sm:block" title="AI estimate">
                  <p className="num text-right text-sm font-semibold">{pct}%</p>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-3"><div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} /></div>
                </div>}
                <ChevronRight size={16} className="shrink-0 text-ink-3 transition-transform group-hover:translate-x-0.5" />
              </Link></li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export function SeniorSupport() {
  const { user } = useAuth()
  const isManager = user?.role === 'manager' || user?.role === 'admin'
  const [v, setV] = useState(0)
  const { data, loading, error, retry } = useAsync(() => historyService.escalations(), [v])
  const update = async (id: string, status: string) => { await historyService.updateEscalation(id, status); setV(x => x + 1) }
  return (
    <div className="page page-mid">
      <PageHeader eyebrow="Team" title="Senior technician support" subtitle={isManager ? 'Escalations from your team.' : 'Your requests for senior help.'} />
      {loading && <Skeleton className="h-40" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && data.length === 0 && <EmptyState icon={<HandHelping size={22} />} title="No escalations" hint="Ask a senior technician from inside a repair session." action={<Link to="/history" className="btn btn-primary">View active repairs</Link>} />}
      <ul className="space-y-2.5">
        {data?.map(e => (
          <li key={e.id} className="card px-5 py-4">
            <div className="flex flex-wrap items-center gap-2"><Link to={`/session/${e.session_id}`} className="font-medium hover:text-teal">{appliances.find(a => a.id === e.appliance_type)?.label ?? 'Repair'} <span className="num text-sm font-normal text-ink-3">{e.session_reference}</span></Link><StatusPill status={e.status} /><span className="text-xs text-ink-3">{e.technician ? `${e.technician} · ` : ''}{when(e.created_at)}</span></div>
            <p className="mt-1 text-sm">{e.reason}</p>
            {e.diagnosis_summary && <p className="text-sm text-ink-2">Diagnosis: {e.diagnosis_summary}</p>}
            {isManager && e.status !== 'resolved' && <div className="mt-2 flex gap-2">{e.status === 'open' && <button onClick={() => void update(e.id, 'in_review')} className="btn btn-sm">Mark in review</button>}<button onClick={() => void update(e.id, 'resolved')} className="btn btn-sm !border-accent/40 !text-accent">Mark resolved</button></div>}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function HelpPage() {
  const nav = useNavigate()
  const { newSession } = useApp()
  const faq = [
    ['What does FixSaathi do?', 'It guides you through a repair by chat, photo or voice, ranks likely faults, marks parts on your photos, gives step-by-step guidance and writes the service report.'],
    ['How does the AI work?', 'FixSaathi uses Google Gemini through its API. For every question it first searches a curated knowledge base of repair records for the same appliance and brand, and gives Gemini those records as evidence. Answers cite the records they use. No custom model has been trained.'],
    ['Which appliances are covered?', 'Washing machines, refrigerators, split ACs, ceiling fans, microwave ovens and water purifiers, plus basic MCB and rooftop-solar guidance. Coverage differs by brand: when no record matches, FixSaathi says so and gives general guidance.'],
    ['Does it verify that power is off?', 'No. The safety checkboxes record your own statements. The server keeps power-sensitive steps locked until you record both, but only your tester can confirm a circuit is dead.'],
    ['Where do my photos go?', 'Photos you send are stored privately with your repair session on the FixSaathi server. Live video frames are not stored, except a single frame when the AI marks a part.'],
    ['Are AI answers always right?', 'No. Confidence values are AI estimates. Check every step and ask a senior technician when unsure.'],
    ['How does voice work?', 'Tap the microphone, speak, then press Done: only then is your message sent. Your browser turns speech into text and Gemini answers through the FixSaathi server. With the speaker on, the answer is read aloud with the best voice on your device. Chrome, Edge and Safari support voice input.'],
  ]
  return (
    <div className="page page-read">
      <PageHeader eyebrow="Support" title="Help and support" subtitle="How FixSaathi works, what it can and cannot do, and how your data is handled." />
      <div className="space-y-2">{faq.map(([q, a]) => <details key={q} className="card group px-5 py-4"><summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-medium marker:hidden">{q}<span className="text-ink-3 transition-transform group-open:rotate-45" aria-hidden>+</span></summary><p className="mt-2 text-sm leading-relaxed text-ink-2">{a}</p></details>)}</div>
      <div className="mt-6 flex flex-wrap gap-3">
        <button onClick={() => { newSession(); nav('/chat') }} className="btn btn-brand"><MessageSquareText size={16} />Ask the assistant</button>
        <Link to="/evaluation" className="btn">View evaluation results</Link>
      </div>
    </div>
  )
}

export function NotFound() {
  return <div className="flex flex-col items-center py-24 text-center"><p className="num font-display text-7xl text-ink-3">404</p><p className="mt-3 text-xl font-semibold">Page not found</p><p className="mt-1 text-sm text-ink-2">The page you opened doesn't exist or has moved.</p><Link to="/" className="btn btn-brand mt-6">Go home</Link></div>
}
