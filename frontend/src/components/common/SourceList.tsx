import { BookOpen, ExternalLink } from 'lucide-react'
import type { SourceRef } from '../../types'

const STATUS: Record<string, string> = { verified_source: 'manufacturer source', technician_reviewed: 'technician reviewed', unverified: 'unverified', synthetic_demo: 'synthetic demo' }

/** Where an AI answer's evidence came from. Only records the server actually retrieved are listed, numbered to match inline citations. */
export function SourceList({ sources }: { sources: SourceRef[] }) {
  return (
    <details className="group mt-2 w-full text-xs text-ink-3">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-full border border-line px-2.5 py-1 transition-colors hover:border-line-2 hover:text-ink-2">
        <BookOpen size={12} className="text-teal" />{sources.length} source{sources.length > 1 ? 's' : ''}
      </summary>
      <ol className="mt-2 space-y-1.5">
        {sources.map((s, i) => (
          <li key={s.record_id} className="flex gap-2 rounded-xl border border-line bg-surface/50 px-3 py-2">
            <span className="mt-px flex h-4 min-w-4 items-center justify-center rounded-full bg-teal/15 px-1 text-[10px] font-semibold text-teal">{i + 1}</span>
            <span className="min-w-0">
              {s.source_url ? <a href={s.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-ink-2 hover:text-teal">{s.source_name}<ExternalLink size={10} /></a> : <span className="text-ink-2">{s.source_name}</span>}
              <span className="block text-[11px] text-ink-3">{s.record_id} · {STATUS[s.verification_status] ?? s.verification_status}{s.related_category ? ' · related category' : ''}</span>
            </span>
          </li>
        ))}
      </ol>
    </details>
  )
}
