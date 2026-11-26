import { Check } from 'lucide-react'

export interface Stage { label: string; done: boolean }

/** The five stages of a repair, in order. Supports interactive switching on mobile guided view and keeps
 *  the isolate stage rendered strictly in power-state colours (red while live, green once isolated). */
export function RepairProgress({
  stages,
  isolateIndex,
  activeIndex,
  onSelect,
}: {
  stages: Stage[]
  isolateIndex: number
  activeIndex?: number
  onSelect?: (index: number) => void
}) {
  const current = stages.findIndex(s => !s.done)
  return (
    <ol aria-label="Repair progress" className="mt-5 grid grid-cols-5 gap-1.5">
      {stages.map((s, i) => {
        const now = i === current
        const selected = activeIndex === i
        const power = i === isolateIndex
        const bar = s.done ? (power ? 'bg-ok' : 'bg-accent') : now ? (power ? 'bg-crit' : 'bg-accent/55') : 'bg-line-2'
        const content = (
          <>
            <span aria-hidden className={`block h-1.5 w-full rounded-full transition-colors duration-300 ${bar}`} />
            <span className={`mt-2 flex items-center justify-center gap-1 sm:justify-start text-[11px] sm:text-xs ${selected ? 'font-semibold text-ink' : s.done ? 'text-ink-2' : now ? 'font-semibold text-ink' : 'text-ink-3'}`}>
              {s.done ? (
                <Check size={12} strokeWidth={3} className={`shrink-0 ${power ? 'text-ok' : 'text-accent'}`} aria-hidden />
              ) : (
                <span className={`num flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[11px] ${selected ? 'bg-accent text-white' : 'bg-surface-2 text-ink-3'}`}>{i + 1}</span>
              )}
              <span className="truncate">{s.label}</span>
              <span className="sr-only">{s.done ? ' (done)' : now ? ' (current)' : ''}</span>
            </span>
          </>
        )
        return (
          <li key={s.label} aria-current={now ? 'step' : undefined} className="min-w-0">
            {onSelect ? (
              <button type="button" onClick={() => onSelect(i)} className={`w-full min-h-[44px] rounded-xl px-1 py-1 text-left transition-colors ${selected ? 'bg-surface-2/80 ring-1 ring-line-2' : 'hover:bg-surface-2/40'}`}>
                {content}
              </button>
            ) : content}
          </li>
        )
      })}
    </ol>
  )
}
