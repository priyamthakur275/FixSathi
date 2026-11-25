import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Clock3, RefreshCw, Star } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState, ErrorState, Skeleton, StatusPill } from '../components/common/ui'
import { dashboardService, historyService } from '../services'
import { useAsync } from '../hooks/useAsync'
import { useCountUp } from '../hooks/useCountUp'
import { useAuth } from '../context/AuthContext'
import type { RepairSession } from '../types'

const tip = { background: 'var(--color-surface)', border: '1px solid var(--color-line-2)', borderRadius: 12, color: 'var(--color-ink)', fontSize: 12, boxShadow: 'var(--shadow-pop)' }
const axis = { stroke: 'var(--color-ink-3)', fontSize: 12 }
const REFRESH_MS = 60_000

/** A figure that counts up to its value when the dashboard loads. */
function Figure({ value, decimals = 0, suffix = '', className = '' }: { value: number | null; decimals?: number; suffix?: string; className?: string }) {
  const v = useCountUp(value)
  if (value === null || v === null) return <span className="text-sm font-normal text-ink-3">Not enough data</span>
  return <span className={`num ${className}`}>{v.toFixed(decimals)}{suffix}</span>
}

/** A thin ring for a rate between 0 and 1, drawn in once. */
function Ring({ rate }: { rate: number | null }) {
  const r = 22, c = 2 * Math.PI * r
  const v = useCountUp(rate === null ? null : rate * 100, 1100)
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" aria-hidden className="-rotate-90">
      <circle cx="28" cy="28" r={r} fill="none" stroke="var(--color-line)" strokeWidth="5" />
      {v !== null && <circle cx="28" cy="28" r={r} fill="none" stroke="var(--color-accent)" strokeWidth="5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} />}
    </svg>
  )
}

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null
  const max = Math.max(1, ...points), w = 96, h = 30
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${(i / (points.length - 1)) * w},${h - (p / max) * (h - 4) - 2}`).join(' ')
  return <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="overflow-visible"><path d={d} fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" /></svg>
}

const ago = (iso: string) => {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000))
  return m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`
}

export default function ManagerDashboard() {
  const { user } = useAuth()
  const allowed = user?.role === 'manager' || user?.role === 'admin'
  const { data, loading, error, retry } = useAsync(() => allowed ? Promise.all([dashboardService.load(), historyService.list()]).then(([d, h]) => ({ ...d, recent: h.items.slice(0, 7), at: new Date() })) : Promise.resolve(null), [allowed])
  const updated = data?.at ?? null
  // A dashboard on a wall screen stays current: it reloads every minute while the tab is visible.
  useEffect(() => {
    if (!allowed) return
    const t = setInterval(() => { if (document.visibilityState === 'visible') retry() }, REFRESH_MS)
    return () => clearInterval(t)
  }, [allowed, retry])
  const spark = useMemo(() => data?.trend.map(p => p.sessions) ?? [], [data])
  if (!allowed) return <div className="mx-auto max-w-3xl px-4 py-10"><EmptyState title="Managers only" hint="Ask an admin to give your account the manager role to see team metrics." /></div>
  const o = data?.overview
  const maxTech = Math.max(1, ...(data?.technicians.map(t => t.sessions) ?? [1]))
  const totalRatings = data?.ratings.reduce((a, r) => a + r.count, 0) ?? 0

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
      <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="font-display text-[28px] leading-tight md:text-[34px]">Team dashboard</h1>
          <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-2">
            <span>{user?.organisation_name ?? 'Your organisation'}</span>
            <span className="inline-flex items-center gap-1.5 text-ink-3" aria-live="polite">
              <span className="relative flex h-2 w-2" aria-hidden><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-accent" /></span>
              {updated ? `Live, updated ${updated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Loading'}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={retry} disabled={loading} className="btn btn-sm" aria-label="Refresh dashboard metrics">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} aria-hidden />Refresh
          </button>
          <Link to="/history" className="btn btn-sm">Team repair history</Link>
          <Link to="/senior" className="btn btn-sm">Escalations</Link>
          <Link to="/reports" className="btn btn-sm">Service reports</Link>
        </div>
      </header>
      {loading && !data && <div className="space-y-4"><Skeleton className="h-36" /><Skeleton className="h-80" /></div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && o && (<>
        {/* Four figures a service manager checks first, in one instrument panel. */}
        <dl className="card grid overflow-hidden sm:grid-cols-2 lg:grid-cols-4 [&>div]:border-line [&>div]:p-5 [&>div]:border-b [&>div:last-child]:border-b-0 sm:[&>div:nth-child(odd)]:border-r sm:[&>div:nth-child(n+3)]:border-b-0 lg:[&>div]:border-r lg:[&>div:last-child]:border-r-0 lg:[&>div]:border-b-0">
          <div>
            <dt className="text-[13px] font-medium text-ink-2">Repair sessions</dt>
            <dd className="mt-3 flex items-end justify-between gap-3">
              <span><Figure value={o.total_sessions} className="font-display block text-[40px] leading-none" /><span className="mt-2 block text-xs text-ink-3">{o.completed} completed, {o.active} active</span></span>
              <Sparkline points={spark} />
            </dd>
          </div>
          <div>
            <dt className="text-[13px] font-medium text-ink-2">First-time fix</dt>
            <dd className="mt-3 flex items-end justify-between gap-3">
              <span><Figure value={o.first_time_fix_rate === null ? null : o.first_time_fix_rate * 100} suffix="%" className="font-display block text-[40px] leading-none" /><span className="mt-2 block text-xs text-ink-3">{o.first_time_fix_sample ? `Of ${o.first_time_fix_sample} completed with outcome` : 'No completed repairs yet'}</span></span>
              <Ring rate={o.first_time_fix_rate} />
            </dd>
          </div>
          <div>
            <dt className="text-[13px] font-medium text-ink-2">Waiting for a senior</dt>
            <dd className="mt-3">
              <Figure value={o.open_escalations} className={`font-display block text-[40px] leading-none ${o.open_escalations ? 'text-warn' : ''}`} />
              <Link to="/senior" className="mt-2 inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink">{o.escalated} escalated in total<ArrowUpRight size={12} aria-hidden /></Link>
            </dd>
          </div>
          <div>
            <dt className="text-[13px] font-medium text-ink-2">Technician rating</dt>
            <dd className="mt-3">
              <span className="flex items-end gap-2"><Figure value={o.avg_rating} decimals={1} className="font-display text-[40px] leading-none" />{o.avg_rating !== null && <span className="mb-1 flex text-amber" role="img" aria-label={`${o.avg_rating} out of 5`}>{[1, 2, 3, 4, 5].map(n => <Star key={n} size={13} className={n <= Math.round(o.avg_rating ?? 0) ? 'fill-current' : 'opacity-30'} aria-hidden />)}</span>}</span>
              <span className="mt-2 block text-xs text-ink-3">{o.ratings_count ? `${o.ratings_count} session ratings` : 'No ratings yet'}</span>
            </dd>
          </div>
        </dl>

        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 rounded-2xl border border-line bg-surface-2/50 px-5 py-4 text-sm md:grid-cols-4">
          {([
            ['Avg repair time', o.avg_repair_minutes === null ? null : `${Math.round(o.avg_repair_minutes)} min`],
            ['Guidance accurate', o.guidance_correct_rate === null ? null : `${Math.round(o.guidance_correct_rate * 100)}%`],
            ['Helpful AI answers', o.answer_helpful_rate === null ? null : `${Math.round(o.answer_helpful_rate * 100)}% of ${o.answers_rated}`],
            ['Avg AI reply', o.avg_ai_latency_ms === null ? null : `${(o.avg_ai_latency_ms / 1000).toFixed(1)} s`],
          ] as const).map(([k, v]) => (
            <div key={k} className="min-w-0"><dt className="text-xs text-ink-3">{k}</dt><dd className={`num mt-0.5 truncate font-semibold ${v === null ? '!font-normal text-ink-3' : ''}`}>{v ?? 'Not enough data'}</dd></div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-ink-3">AI cost per repair: {o.ai_cost_per_repair ?? o.ai_cost_note}</p>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.65fr_1fr]">
          <section className="card card-pad flex flex-col" aria-labelledby="trend-h">
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="trend-h" className="font-display text-[17px]">Repairs, last 7 days</h2>
              <span className="flex items-center gap-4 text-xs text-ink-2">
                <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-accent" aria-hidden />Started</span>
                <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-teal" aria-hidden />Completed</span>
              </span>
            </div>
            <div className="h-72 w-full flex-1 lg:min-h-72" role="img" aria-label="Area chart of repair sessions started and completed per day">
              <ResponsiveContainer>
                <AreaChart data={data.trend} margin={{ left: -18, right: 6, top: 8 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.32} /><stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} /></linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--color-teal)" stopOpacity={0.28} /><stop offset="100%" stopColor="var(--color-teal)" stopOpacity={0} /></linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--color-line)" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="day" {...axis} tickLine={false} axisLine={false} /><YAxis {...axis} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={tip} cursor={{ stroke: 'var(--color-line-2)' }} />
                  <Area type="monotone" dataKey="sessions" name="Started" stroke="var(--color-accent)" strokeWidth={2.25} fill="url(#g1)" animationDuration={1100} />
                  <Area type="monotone" dataKey="completed" name="Completed" stroke="var(--color-teal)" strokeWidth={2.25} fill="url(#g2)" animationDuration={1300} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="card card-pad" aria-labelledby="feed-h">
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h2 id="feed-h" className="font-display text-[17px]">Latest repairs</h2>
              <Link to="/history" className="text-xs text-ink-3 hover:text-ink">All</Link>
            </div>
            {data.recent.length === 0 ? <p className="py-8 text-center text-sm text-ink-3">Repairs from your team appear here as they start.</p> :
              <ul className="-mx-2">
                {data.recent.map((r: RepairSession) => (
                  <li key={r.id}>
                    <Link to={`/session/${r.id}`} className="flex items-center gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-surface-2">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-3 text-[12px] font-semibold text-ink-2" aria-hidden>{(r.technician_name ?? '?').trim()[0]}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13.5px] font-medium">{r.title.replace(/^Demo: /, '')}</span>
                        <span className="flex items-center gap-1 text-xs text-ink-3"><Clock3 size={11} aria-hidden />{r.technician_name ?? 'Technician'}, {ago(r.started_at)}</span>
                      </span>
                      <StatusPill status={r.status} />
                    </Link>
                  </li>
                ))}
              </ul>}
          </section>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.65fr_1fr]">
          <section className="card card-pad" aria-labelledby="tech-h">
            <h2 id="tech-h" className="font-display mb-4 text-[17px]">Technicians</h2>
            {data.technicians.length === 0 ? <p className="py-8 text-center text-sm text-ink-3">Sessions from your team appear here.</p> :
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-ink-3"><th className="pb-2 font-medium">Name</th><th className="pb-2 font-medium">Sessions</th><th className="num pb-2 text-right font-medium">Done</th><th className="num pb-2 text-right font-medium">Escalated</th></tr></thead>
                <tbody>
                  {[...data.technicians].sort((a, b) => b.sessions - a.sessions).map(t => (
                    <tr key={t.name} className="border-t border-line">
                      <td className="py-3 pr-3 font-medium">{t.name}</td>
                      <td className="w-1/2 py-3 pr-4">
                        <span className="flex items-center gap-2.5"><span className="h-2 flex-1 overflow-hidden rounded-full bg-surface-3"><span className="fs-grow block h-full rounded-full bg-accent" style={{ width: `${(t.sessions / maxTech) * 100}%` }} /></span><span className="num w-6 text-right text-ink-2">{t.sessions}</span></span>
                      </td>
                      <td className="num py-3 text-right text-ink-2">{t.completed}</td>
                      <td className={`num py-3 text-right ${t.escalated ? 'text-warn' : 'text-ink-3'}`}>{t.escalated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>}
          </section>
          <section className="card card-pad" aria-labelledby="rate-h">
            <div className="mb-4 flex items-baseline justify-between gap-2">
              <h2 id="rate-h" className="font-display text-[17px]">Ratings</h2>
              <span className="text-xs text-ink-3">{totalRatings} total</span>
            </div>
            {totalRatings === 0 ? <p className="py-8 text-center text-sm text-ink-3">Technicians rate the guidance when they finish a session.</p> :
              <ul className="space-y-2.5">
                {data.ratings.map(r => (
                  <li key={r.stars} className="flex items-center gap-3 text-sm">
                    <span className="num flex w-8 items-center gap-1 text-ink-2">{r.stars}<Star size={11} className="fill-current text-amber" aria-hidden /></span>
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-surface-3"><span className="fs-grow block h-full rounded-full bg-amber" style={{ width: `${(r.count / totalRatings) * 100}%` }} /></span>
                    <span className="num w-6 text-right text-ink-2">{r.count}</span>
                  </li>
                ))}
              </ul>}
          </section>
        </div>
      </>)}
    </div>
  )
}
