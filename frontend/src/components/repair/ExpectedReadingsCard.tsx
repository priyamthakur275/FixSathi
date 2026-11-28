import { useEffect, useState } from 'react'
import { Gauge, ShieldAlert } from 'lucide-react'
import { lookupService, type ExpectedReading, type ExpectedReadingsResponse } from '../../services'

const CONDITION_LABEL: Record<ExpectedReading['condition'], string> = {
  isolated_and_discharged: 'Off-circuit (MCB off & discharged)',
  visual_or_non_contact: 'Display / visual check',
  authorised_service_only: 'Authorised service only',
}

export function ExpectedReadingsCard({ appliance }: { appliance?: string }) {
  const [data, setData] = useState<ExpectedReadingsResponse | null>(null)

  useEffect(() => {
    let live = true
    lookupService.expectedReadings(appliance).then(r => {
      if (live && r && Array.isArray(r.items)) setData(r)
    }).catch(() => undefined)
    return () => { live = false }
  }, [appliance])

  if (!data || data.items.length === 0) return null

  return (
    <div className="mt-4 rounded-2xl border border-line bg-surface-2/40 p-4 text-sm" role="region" aria-label="Expected readings reference">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Gauge size={16} className="text-teal" aria-hidden />
          <h3 className="font-semibold text-ink">Expected readings</h3>
        </div>
        <span className="rounded-full border border-teal/40 bg-teal/10 px-2.5 py-0.5 text-[11px] font-medium text-teal">
          Reference only · Not live-work guidance
        </span>
      </div>

      <ul className="mt-3 space-y-2.5">
        {data.items.map(item => (
          <li key={item.id} className="rounded-xl border border-line bg-surface p-3 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold text-ink">
                {item.parameter} <span className="font-normal text-ink-3">· {item.hindi_name}</span>
              </p>
              <span className="rounded-md border border-line bg-surface-2 px-2 py-0.5 text-[11px] text-ink-2">
                {CONDITION_LABEL[item.condition] ?? item.condition}
              </span>
            </div>
            <p className="mt-1.5 font-mono text-xs font-medium text-accent">Expected: {item.expected_range}</p>
            <p className="mt-1 text-ink-2">If outside range: {item.out_of_range_meaning}</p>
          </li>
        ))}
      </ul>

      <p className="mt-3 flex items-start gap-2 rounded-xl border border-warn/35 bg-warn/10 px-3 py-2 text-xs text-ink-2">
        <ShieldAlert size={14} className="mt-0.5 shrink-0 text-warn" aria-hidden />
        <span>{data.disclaimer}</span>
      </p>
    </div>
  )
}
