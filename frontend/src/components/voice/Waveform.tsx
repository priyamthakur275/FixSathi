import { useEffect, useRef } from 'react'

const BARS = 32

/** Bars driven by the real microphone level (newest on the right), so the technician can see that they are being heard. */
export function LiveWaveform({ level, className = '' }: { level: () => number; className?: string }) {
  const bars = useRef<(HTMLSpanElement | null)[]>([])
  useEffect(() => {
    const hist = new Array(BARS).fill(0)
    let raf = 0; let last = 0
    const tick = (t: number) => {
      raf = requestAnimationFrame(tick)
      if (t - last < 55) return
      last = t
      hist.shift(); hist.push(level())
      hist.forEach((v, i) => { const el = bars.current[i]; if (el) el.style.transform = `scaleY(${Math.max(0.12, Math.min(1, v * 1.4))})` })
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [level])
  return (
    <div className={`flex h-8 items-center gap-[3px] ${className}`} aria-hidden>
      {Array.from({ length: BARS }).map((_, i) => <span key={i} ref={el => { bars.current[i] = el }} className="h-full w-[3px] origin-center rounded-full bg-accent transition-transform duration-75" style={{ transform: 'scaleY(.12)' }} />)}
    </div>
  )
}
