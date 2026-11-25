import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AirVent, Fan, Loader2, PlayCircle, ShieldCheck } from 'lucide-react'
import { demoService } from '../services'
import { useAsync } from '../hooks/useAsync'
import { useApp } from '../context/AppContext'

const ICON: Record<string, typeof Fan> = { ceiling_fan: Fan, split_ac: AirVent }

/** Labelled demo scenarios: scripted sample content, run through the real server, safety gate and reports. */
export default function DemoPage() {
  const nav = useNavigate()
  const { openSession } = useApp()
  const { data, error, loading } = useAsync(() => demoService.list(), [])
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const start = async (id: string) => {
    setBusy(id); setErr(null)
    try { const s = await demoService.start(id); await openSession(s.id); nav(`/chat/${s.id}`) }
    catch (e) { setErr((e as Error).message || 'Could not start the demo.') } finally { setBusy(null) }
  }
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 md:px-8">
      <h1 className="font-display text-[26px] leading-tight md:text-[34px]">Demo scenarios</h1>
      <p className="mt-2 max-w-2xl text-ink-2">Walk through a complete repair even when live AI is unavailable. Replies, diagnosis and steps in these sessions are <b className="text-ink">scripted sample content written by our team, not live AI</b>, and every screen says so.</p>
      <div className="mt-5 flex max-w-2xl items-start gap-3 rounded-2xl border border-teal/30 bg-teal/[0.07] px-4 py-3.5 text-sm text-ink-2">
        <ShieldCheck size={18} className="mt-0.5 shrink-0 text-teal" />
        <span>What is real: your login, the session, the photo, the knowledge-base sources, the <b className="text-ink">server-side safety lock</b>, the event log and the service report. Demo mode cannot skip the safety checks.</span>
      </div>
      {loading && <p className="mt-8 flex items-center gap-2 text-ink-3"><Loader2 className="animate-spin" size={16} />Loading scenarios...</p>}
      {(error || err) && <p role="alert" className="mt-6 rounded-2xl border border-crit/40 bg-crit/10 px-4 py-3 text-sm text-crit">{err || error}</p>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {data?.items.map(sc => { const I = ICON[sc.appliance] ?? PlayCircle
          return (
            <div key={sc.id} className="card card-hover card-pad flex flex-col">
              <div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-surface-2 text-accent"><I size={22} /></span><h2 className="font-display text-[16px] leading-snug">{sc.title}</h2></div>
              <p className="mt-3 flex-1 text-sm text-ink-2">{sc.issue}</p>
              <p className="mt-2 text-xs text-ink-3">{sc.has_photo ? 'Includes a real photo of the fault.' : 'Text only, no photo.'}</p>
              <button onClick={() => void start(sc.id)} disabled={!!busy} className="btn btn-primary mt-5 py-2.5">
                {busy === sc.id ? <Loader2 size={18} className="animate-spin" /> : <PlayCircle size={18} />}Start demo session</button>
            </div>) })}
      </div>
    </div>
  )
}
