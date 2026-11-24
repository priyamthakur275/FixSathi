import { useMemo, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { ChevronRight, History, Search } from 'lucide-react'
import { EmptyState, ErrorState, PageHeader, Skeleton, StatusPill } from '../components/common/ui'
import { historyService } from '../services'
import { useAsync } from '../hooks/useAsync'

export default function RepairHistoryPage({ mine = false }: { mine?: boolean }) {
  const { data, loading, error, retry } = useAsync(() => historyService.list(mine), [mine])
  const [q, setQ] = useState('')
  const rows = useMemo(() => {
    const t = q.trim().toLowerCase()
    return (data?.items ?? []).filter(r => !t || [r.title, r.reference, r.appliance_label, r.technician_name ?? ''].some(v => v.toLowerCase().includes(t)))
  }, [data, q])
  const tab = ({ isActive }: { isActive: boolean }) => `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${isActive ? 'bg-surface-3 text-ink shadow-[inset_0_0_0_1px_var(--color-line-2)]' : 'text-ink-2 hover:text-ink'}`
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
      <PageHeader eyebrow="Workspace" title={mine ? 'My Repairs' : 'Repair History'} subtitle={mine ? 'Repairs that are still open or escalated.' : 'Repair sessions you are allowed to see.'}
        right={<div className="flex rounded-xl border border-line bg-surface/60 p-1"><NavLink to="/history" className={tab}>All</NavLink><NavLink to="/repairs" className={tab}>Open</NavLink></div>} />
      {data && data.items.length > 0 && (
        <div className="relative mb-4 max-w-sm">
          <Search size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-3" />
          <label className="sr-only" htmlFor="hist-q">Search repairs</label>
          <input id="hist-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Search by issue, reference or appliance" className="field !py-2.5 !pl-10 text-sm" />
        </div>
      )}
      {loading && <div className="space-y-3">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-16" />)}</div>}
      {error && <ErrorState message={error} onRetry={retry} />}
      {data && data.items.length === 0 && <EmptyState icon={<History size={22} />} title={mine ? 'Nothing open right now' : 'No repairs yet'} hint="Start a new repair session from the home screen." action={<Link to="/" className="btn btn-brand">Start a repair</Link>} />}
      {data && data.items.length > 0 && rows.length === 0 && <p className="py-10 text-center text-sm text-ink-2">No repairs match “{q}”.</p>}
      {rows.length > 0 && (<>
        <div className="card hidden overflow-hidden md:block">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-surface-2/40 text-[11px] uppercase tracking-wider text-ink-3"><tr>{['Appliance', 'Session', 'Started', 'Technician', 'Issue', 'Status', ''].map(h => <th key={h} className="px-4 py-3 font-semibold">{h}</th>)}</tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id} className="border-b border-line/60 transition-colors last:border-0 hover:bg-surface-2/40">
                  <td className="px-4 py-3.5 font-medium">{r.appliance_label}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-ink-2"><Link className="hover:text-teal" to={`/session/${r.id}`}>{r.reference}</Link></td>
                  <td className="px-4 py-3.5 text-ink-2">{new Date(r.started_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3.5 text-ink-2">{r.technician_name}</td>
                  <td className="max-w-[280px] truncate px-4 py-3.5 text-ink-2" title={r.title}>{r.title}</td>
                  <td className="px-4 py-3.5"><StatusPill status={r.status} /></td>
                  <td className="px-4 py-3.5 text-right">{r.report_id ? <Link to={`/reports/${r.report_id}`} className="inline-flex items-center gap-1 font-medium text-teal hover:underline">Report<ChevronRight size={14} /></Link> : <Link to={`/session/${r.id}`} className="inline-flex items-center gap-1 font-medium text-teal hover:underline">Open<ChevronRight size={14} /></Link>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul className="space-y-2 md:hidden">
          {rows.map(r => (
            <li key={r.id}><Link to={r.report_id ? `/reports/${r.report_id}` : `/session/${r.id}`} className="card card-hover flex items-center gap-3 p-4">
              <div className="min-w-0 flex-1"><p className="text-xs text-ink-3">{r.appliance_label} · {r.reference} · {new Date(r.started_at).toLocaleDateString()}</p><p className="mt-0.5 truncate font-medium">{r.title}</p><div className="mt-2"><StatusPill status={r.status} /></div></div>
              <ChevronRight size={16} className="text-ink-3" /></Link></li>
          ))}
        </ul>
      </>)}
    </div>
  )
}
