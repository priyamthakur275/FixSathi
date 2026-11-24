import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react'

export function DemoBadge({ children = 'Sample data' }: { children?: ReactNode }) {
  return <span className="inline-flex items-center rounded-full border border-warn/40 bg-warn/10 px-2.5 py-0.5 text-[11px] font-medium text-warn">{children}</span>
}

const PILL: Record<string, string> = {
  completed: 'text-ok bg-ok/10 border-ok/30', resolved: 'text-ok bg-ok/10 border-ok/30',
  escalated: 'text-warn bg-warn/10 border-warn/30', awaiting_confirmation: 'text-warn bg-warn/10 border-warn/30', open: 'text-warn bg-warn/10 border-warn/30',
  cancelled: 'text-ink-3 border-line', not_resolved: 'text-crit bg-crit/10 border-crit/30',
}
const DOT: Record<string, string> = { completed: 'bg-ok', resolved: 'bg-ok', escalated: 'bg-warn', awaiting_confirmation: 'bg-warn', open: 'bg-warn', cancelled: 'bg-ink-3', not_resolved: 'bg-crit' }

export function StatusPill({ status }: { status: string }) {
  const label = status.replace(/_/g, ' ')
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${PILL[status] ?? 'text-teal bg-teal/10 border-teal/30'}`}><span className={`h-1.5 w-1.5 rounded-full ${DOT[status] ?? 'bg-teal'}`} aria-hidden />{label}</span>
}

export function Skeleton({ className = '' }: { className?: string }) { return <div className={`skeleton ${className}`} aria-hidden /> }

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-warn/10 text-warn"><AlertTriangle size={22} /></span>
      <p className="max-w-md text-ink-2">{message}</p>
      <button onClick={onRetry} className="btn"><RefreshCw size={14} />Try again</button>
    </div>
  )
}

export function EmptyState({ title, hint, icon, action }: { title: string; hint: string; icon?: ReactNode; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center px-6 py-14 text-center">
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-line-2 bg-surface-2 text-ink-3">{icon ?? <Inbox size={22} />}</span>
      <p className="font-semibold">{title}</p><p className="mt-1 max-w-sm text-sm text-ink-2">{hint}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function PageHeader({ title, subtitle, right, eyebrow }: { title: string; subtitle?: string; right?: ReactNode; eyebrow?: string }) {
  return (
    <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">{eyebrow && <p className="section-label mb-2 text-teal">{eyebrow}</p>}<h1 className="text-2xl font-semibold tracking-tight md:text-[32px] md:leading-tight">{title}</h1>{subtitle && <p className="mt-1.5 max-w-2xl text-sm text-ink-2">{subtitle}</p>}</div>
      {right}
    </header>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`card card-pad ${className}`}>{children}</section>
}

export function SectionTitle({ id, icon, children, right }: { id?: string; icon?: ReactNode; children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 id={id} className="flex items-center gap-2.5 text-[15px] font-semibold">{icon && <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-surface-3 text-teal">{icon}</span>}{children}</h2>
      {right}
    </div>
  )
}
