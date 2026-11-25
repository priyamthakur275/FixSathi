import { useEffect, useRef, useState } from 'react'

const reduced = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** Counts from the previous value to `target` over `ms`, easing out. Jumps straight there when motion is reduced. */
export function useCountUp(target: number | null, ms = 900): number | null {
  const [v, setV] = useState<number | null>(target === null || reduced() ? target : 0)
  const from = useRef(0)
  useEffect(() => {
    if (target === null) return
    if (reduced()) { from.current = target; const id = requestAnimationFrame(() => setV(target)); return () => cancelAnimationFrame(id) }
    const start = performance.now(); const a = from.current
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / ms); const e = 1 - Math.pow(1 - k, 3)
      setV(a + (target - a) * e)
      if (k < 1) raf = requestAnimationFrame(tick); else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return target === null ? null : v
}
