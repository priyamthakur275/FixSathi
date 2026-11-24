import { Link } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState, ErrorState, PageHeader, Skeleton } from '../components/common/ui'
import { dashboardService } from '../services'
import { useAsync } from '../hooks/useAsync'
import { useAuth } from '../context/AuthContext'

const tip = { background: 'var(--color-surface)', border: '1px solid var(--color-line-2)', borderRadius: 12, color: 'var(--color-ink)', fontSize: 12, boxShadow: 'var(--shadow-pop)' }
const axis = { stroke: 'var(--color-ink-3)', fontSize: 12 }
const pct = (v: number | null) => v === null ? null : `${Math.round(v * 100)}%`

export default function ManagerDashboard() {
  const { user } = useAuth()
  const allowed = user?.role === 'manager' || user?.role === 'admin'
  const { data, loading, error, retry } = useAsync(() => allowed ? dashboardService.load() : Promise.resolve(null), [allowed])
  if (!allowed) return <div className="mx-auto max-w-3xl px-4 py-10"><EmptyState title="Managers only" hint="Ask an admin to give your account the manager role to see team metrics." /></div>
  const o = data?.overview
  const kpis: [string, string | null, string | null][] = o ? [
    ['Total sessions', String(o.total_sessions), `${o.completed} completed`],
    ['Active now', String(o.active), 'In progress'],
    ['Escalated', String(o.escalated), `${o.open_escalations} open requests`],
    ['First-time fix', pct(o.first_time_fix_rate), o.first_time_fix_rate !== null ? `${o.first_time_fix_sample} completed with outcome` : null],
    ['Avg repair time', o.avg_repair_minutes === null ? null : `${o.avg_repair_minutes} min`, o.completed ? `Across ${o.completed} completed` : null],
    ['Avg AI reply', o.avg_ai_latency_ms === null ? null : `${(o.avg_ai_latency_ms / 1000).toFixed(1)}s`, 'Successful AI turns'],
    ['Helpful answers', pct(o.answer_helpful_rate), o.answers_rated ? `${o.answers_helpful} of ${o.answers_rated} rated answers` : null],
    ['Avg rating', o.avg_rating === null ? null : `${o.avg_rating} / 5`, o.ratings_count ? `${o.ratings_count} session ratings` : null],
  ] : []

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
      <PageHeader
        eyebrow="Team"
        title="Manager workspace"
        subtitle={`Live operational telemetry for ${user?.organisation_name ?? 'your organisation'}. Metrics show "Not enough data" until records exist.`}
        right={
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={retry} disabled={loading} className="btn btn-sm inline-flex items-center gap-1.5" aria-label="Refresh dashboard metrics">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} aria-hidden />
              Refresh
            </button>
            <Link to="/history" className="btn btn-sm">Team repair history</Link>
            <Link to="/senior" className="btn btn-sm">Escalations</Link>
            <Link to="/reports" className="btn btn-sm">Service reports</Link>
          </div>
        }
      />
      {loading && !data && <div className="space-y-4"><Skeleton className="h-28" /><Skeleton className="h-72" /></div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && o && (<>
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {kpis.map(([k, v, sub]) => (
            <div key={k} className="card px-4 py-4">
              <dt className="text-xs font-medium text-ink-2">{k}</dt>
              <dd className="mt-2 text-[26px] font-semibold leading-none tabular-nums">
                {v === null ? <span className="text-sm font-normal text-ink-3">Not enough data</span> : <span className="fs-grad-text">{v}</span>}
              </dd>
              {sub && <p className="mt-1.5 text-[11px] text-ink-3">{sub}</p>}
            </div>
          ))}
        </dl>
        <p className="mt-3 text-xs text-ink-3">AI cost per repair: {o.ai_cost_per_repair ?? o.ai_cost_note}</p>
        <section className="card card-pad mt-6" aria-labelledby="trend-h">
          <h2 id="trend-h" className="mb-3 font-semibold">Repair sessions, last 7 days</h2>
          <div className="h-72 w-full" role="img" aria-label="Area chart of sessions and completed sessions per day">
            <ResponsiveContainer>
              <AreaChart data={data.trend} margin={{ left: -16, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#38bdf8" stopOpacity={0.4} /><stop offset="100%" stopColor="#38bdf8" stopOpacity={0} /></linearGradient>
                  <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.35} /><stop offset="100%" stopColor="#2dd4bf" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid stroke="var(--color-line)" vertical={false} /><XAxis dataKey="day" {...axis} tickLine={false} axisLine={false} /><YAxis {...axis} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={tip} /><Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: 'var(--color-ink-2)' }} />
                <Area type="monotone" dataKey="sessions" name="Sessions" stroke="#38bdf8" strokeWidth={2} fill="url(#g1)" /><Area type="monotone" dataKey="completed" name="Completed" stroke="#2dd4bf" strokeWidth={2} fill="url(#g2)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="card card-pad" aria-labelledby="tech-h">
            <h2 id="tech-h" className="mb-3 font-semibold">Technician activity</h2>
            {data.technicians.length === 0 ? <EmptyState title="No technician activity yet" hint="Sessions from your team appear here." /> :
              <div className="h-64" role="img" aria-label="Bar chart of sessions per technician"><ResponsiveContainer><BarChart data={data.technicians} margin={{ left: -16 }}><CartesianGrid stroke="var(--color-line)" vertical={false} /><XAxis dataKey="name" {...axis} tickLine={false} axisLine={false} /><YAxis {...axis} tickLine={false} axisLine={false} allowDecimals={false} /><Tooltip contentStyle={tip} cursor={{ fill: '#162133' }} /><Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: 'var(--color-ink-2)' }} /><Bar dataKey="sessions" name="Sessions" fill="#5b8cff" radius={[6, 6, 0, 0]} /><Bar dataKey="escalated" name="Escalated" fill="#fbbf24" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>}
          </section>
          <section className="card card-pad" aria-labelledby="rate-h">
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h2 id="rate-h" className="font-semibold">Feedback ratings</h2>
              {o.guidance_correct_rate !== null && (
                <span className="text-xs text-ink-3">Guidance accurate: <strong className="text-ink">{pct(o.guidance_correct_rate)}</strong></span>
              )}
            </div>
            {data.ratings.every(r => r.count === 0) ? <EmptyState title="No ratings yet" hint="Technicians rate the guidance when they finish a session." /> :
              <div className="h-64" role="img" aria-label="Bar chart of rating counts"><ResponsiveContainer><BarChart data={data.ratings} layout="vertical"><XAxis type="number" {...axis} tickLine={false} axisLine={false} allowDecimals={false} /><YAxis type="category" dataKey="stars" {...axis} tickLine={false} axisLine={false} width={28} /><Tooltip contentStyle={tip} cursor={{ fill: '#162133' }} /><Bar dataKey="count" name="Ratings" radius={[0, 6, 6, 0]}>{data.ratings.map((_, i) => <Cell key={i} fill={['#2dd4bf', '#38bdf8', '#5b8cff', '#ff9f43', '#75839b'][i]} />)}</Bar></BarChart></ResponsiveContainer></div>}
          </section>
        </div>
      </>)}
    </div>
  )
}
