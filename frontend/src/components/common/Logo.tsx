interface Props { className?: string; height?: number }

/** Original supplied emblem. Aspect ratio preserved (height drives width). */
export function Emblem({ height = 40, className = '' }: Props) {
  return <img src="/assets/emblem.png" alt="FixSaathi emblem" style={{ height, width: 'auto' }} className={`select-none ${className}`} draggable={false} />
}

/** The wordmark as live text in the brand colours, so it stays readable on both the dark and the light theme
 *  (the supplied wordmark image has a light-grey "Saathi" that disappears on white). `height` is the cap height in pixels. */
export function Wordmark({ height = 28, className = '' }: Props) {
  return (
    <span aria-label="FixSaathi" role="img" className={`select-none whitespace-nowrap font-semibold leading-none tracking-tight ${className}`} style={{ fontSize: Math.round(height * 1.35) }}>
      <span className="text-[#3b9be6]" aria-hidden>Fix</span><span className="text-ink" aria-hidden>Saathi</span>
    </span>
  )
}
