import { Check } from 'lucide-react'

export interface Stage { label: string; done: boolean }

/** The five stages of a repair, in order. The first stage not done is the current one. The isolate stage is drawn in the
 *  power colours: red while the circuit is live, green once the statements are recorded. */
export function RepairProgress({ stages, isolateIndex }: { stages: Stage[]; isolateIndex: number }) {
  const current = stages.findIndex(s => !s.done)
  return (
    <ol aria-label="Repair progress" className="mt-5 grid grid-cols-5 gap-1.5">
      {stages.map((s, i) => {
        const now = i === current
        const power = i === isolateIndex
        const bar = s.done ? (power ? 'bg-ok' : 'bg-accent') : now ? (power ? 'bg-crit' : 'bg-accent/45') : 'bg-line-2'
        return (
          <li key={s.label} aria-current={now ? 'step' : undefined} className="min-w-0">
            <span aria-hidden className={`block h-1.5 rounded-full transition-colors duration-500 ${bar}`} />
            <span className={`mt-2 flex items-center gap-1.5 truncate text-[12px] ${s.done ? 'text-ink-2' : now ? 'font-semibold text-ink' : 'text-ink-3'}`}>
              {s.done ? <Check size={12} strokeWidth={3} className={power ? 'text-ok' : 'text-accent'} aria-hidden /> : <span className="num text-[12px]">{i + 1}</span>}
              <span className={now ? 'truncate' : 'sr-only truncate sm:not-sr-only'}>{s.label}</span>
              <span className="sr-only">{s.done ? ' (done)' : now ? ' (current)' : ''}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}
