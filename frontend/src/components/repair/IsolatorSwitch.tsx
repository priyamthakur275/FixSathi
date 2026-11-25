/** A drawing of the MCB the technician has just switched off. It shows what the server has recorded, nothing more: the lever
 *  drops to OFF and the window turns earth green only when both statements are on record. The checkboxes beside it are the
 *  real controls; this is aria-hidden. */
export function IsolatorSwitch({ isolated, size = 88 }: { isolated: boolean; size?: number }) {
  const w = Math.round(size * 0.64)
  return (
    <svg width={w} height={size} viewBox="0 0 64 100" aria-hidden className="shrink-0 drop-shadow-sm">
      <defs>
        <linearGradient id="mcb-body" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--color-surface)" />
          <stop offset="100%" stopColor="var(--color-surface-3)" />
        </linearGradient>
      </defs>
      {/* DIN-rail body */}
      <rect x="2" y="2" width="60" height="96" rx="9" fill="url(#mcb-body)" stroke="var(--color-line-2)" strokeWidth="1.5" />
      <rect x="2" y="44" width="60" height="12" fill="var(--color-surface-3)" opacity=".6" />
      {/* state window */}
      <rect x="20" y="7" width="24" height="7" rx="2.5" fill={isolated ? 'var(--color-ok)' : 'var(--color-crit)'} style={{ transition: 'fill .35s ease' }} />
      {/* lever slot */}
      <rect x="22" y="24" width="20" height="56" rx="6" fill="var(--color-bg-2)" stroke="var(--color-line-2)" />
      <text x="32" y="21.5" textAnchor="middle" fontSize="6.5" fontWeight="700" fill="var(--color-ink-3)" style={{ fontStretch: '120%' }}>ON</text>
      <text x="32" y="89" textAnchor="middle" fontSize="6.5" fontWeight="700" fill="var(--color-ink-3)" style={{ fontStretch: '120%' }}>OFF</text>
      {/* lever: up = ON (live), down = OFF (isolated) */}
      <g style={{ transform: `translateY(${isolated ? 24 : 0}px)`, transition: 'transform .45s cubic-bezier(.5,1.6,.4,1)' }}>
        <rect x="24.5" y="33" width="15" height="22" rx="4" fill={isolated ? 'var(--color-ok)' : 'var(--color-ink-2)'} style={{ transition: 'fill .35s ease' }} />
        <rect x="27" y="36" width="10" height="2" rx="1" fill="var(--color-surface)" opacity=".55" />
        <rect x="27" y="40" width="10" height="2" rx="1" fill="var(--color-surface)" opacity=".55" />
      </g>
    </svg>
  )
}
