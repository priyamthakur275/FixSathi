import { useEffect, useState } from 'react'
import { mediaUrl } from '../../services/api'
import type { Box } from '../../types'

/** Protected images need the bearer token, so they are fetched and shown through an object URL. */
export function AuthImage({ src, alt, className = '', box, label }: { src: string; alt: string; className?: string; box?: Box | null; label?: string | null }) {
  const [url, setUrl] = useState<string | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let live = true; let made: string | null = null
    mediaUrl(src).then(u => { made = u; if (live) setUrl(u) }).catch(() => live && setErr(true))
    return () => { live = false; if (made) URL.revokeObjectURL(made) }
  }, [src])
  if (err) return <div className={`flex items-center justify-center bg-surface text-xs text-ink-3 ${className}`}>Image unavailable</div>
  if (!url) return <div className={`skeleton ${className}`} />
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <img src={url} alt={alt} className="h-full w-full object-contain" />
      {box && (
        <div className="absolute border-2 border-amber shadow-[0_0_0_2000px_rgba(0,0,0,0.25)]" style={{ left: `${box.x_min / 10}%`, top: `${box.y_min / 10}%`, width: `${(box.x_max - box.x_min) / 10}%`, height: `${(box.y_max - box.y_min) / 10}%` }}>
          {label && <span className="absolute -top-6 left-0 whitespace-nowrap rounded bg-amber px-1.5 py-0.5 text-[11px] font-semibold text-bg">{label}</span>}
        </div>
      )}
    </div>
  )
}
