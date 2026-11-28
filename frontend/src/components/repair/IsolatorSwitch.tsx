/** A drawing of the MCB the technician has just switched off. It shows what the server has recorded, nothing more: the lever
 *  drops to OFF and the window turns earth green only when both statements are on record. The checkboxes beside it are the
 *  real controls; this is aria-hidden. */
export function IsolatorSwitch({ isolated, size = 104 }: { isolated: boolean; size?: number }) {
  const w = Math.round(size * 0.66)
  return (
    <svg width={w} height={size} viewBox="0 0 66 100" aria-hidden className="shrink-0 drop-shadow-sm">
      <defs>
        <linearGradient id="mcb-body" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--color-surface)" />
          <stop offset="100%" stopColor="var(--color-surface-3)" />
        </linearGradient>
      </defs>
      {/* DIN-rail housing */}
      <rect x="2" y="2" width="62" height="96" rx="10" fill="url(#mcb-body)" stroke={isolated ? 'var(--color-ok)' : 'var(--color-crit)'} strokeWidth="2" style={{ transition: 'stroke .35s ease' }} />
      <rect x="2" y="44" width="62" height="12" fill="var(--color-surface-3)" opacity=".65" />
      {/* State indicator window */}
      <rect x="16" y="7" width="34" height="9" rx="3" fill={isolated ? 'var(--color-ok)' : 'var(--color-crit)'} style={{ transition: 'fill .35s ease' }} />
      <text x="33" y="13.5" textAnchor="middle" fontSize="5.5" fontWeight="700" fill="#ffffff">{isolated ? 'ISOLATED' : 'LIVE'}</text>
      {/* Lever slot */}
      <rect x="23" y="25" width="20" height="55" rx="6" fill="var(--color-bg-2)" stroke="var(--color-line-2)" />
      <text x="33" y="22.5" textAnchor="middle" fontSize="6.5" fontWeight="700" fill="var(--color-ink-3)" style={{ fontStretch: '120%' }}>ON</text>
      <text x="33" y="89.5" textAnchor="middle" fontSize="6.5" fontWeight="700" fill="var(--color-ink-3)" style={{ fontStretch: '120%' }}>OFF</text>
      {/* Lever: up = ON (live), down = OFF (isolated) */}
      <g style={{ transform: `translateY(${isolated ? 23 : 0}px)`, transition: 'transform .45s cubic-bezier(.5,1.5,.4,1)' }}>
        <rect x="25.5" y="33" width="15" height="22" rx="4" fill={isolated ? 'var(--color-ok)' : 'var(--color-crit)'} style={{ transition: 'fill .35s ease' }} />
        <rect x="28" y="36.5" width="10" height="2" rx="1" fill="#ffffff" opacity=".6" />
        <rect x="28" y="40.5" width="10" height="2" rx="1" fill="#ffffff" opacity=".6" />
      </g>
    </svg>
  )
}
