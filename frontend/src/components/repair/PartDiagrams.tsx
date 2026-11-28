import type { ReactNode } from 'react'

export type PartDiagramId =
  | 'capacitor'
  | 'mcb'
  | 'drain_pump'
  | 'compressor_relay'
  | 'ro_membrane'
  | 'pcb_board'
  | 'fan_canopy'
  | 'ac_filter_coil'
  | 'solar_isolator'
  | 'generic_part'

export interface PartSpec {
  id: PartDiagramId
  title: string
  hindiName: string
  cue: string
}

export const PART_SPECS: Record<PartDiagramId, PartSpec> = {
  capacitor: {
    id: 'capacitor',
    title: 'Run / Start Capacitor',
    hindiName: 'कैपेसिटर / कंडेनसर',
    cue: 'Cylindrical white or silver can with two insulated leads or spade terminals.',
  },
  mcb: {
    id: 'mcb',
    title: 'MCB / Main Isolator',
    hindiName: 'MCB / मेन स्विच',
    cue: 'DIN-rail breaker switch controlling phase supply to the circuit.',
  },
  drain_pump: {
    id: 'drain_pump',
    title: 'Drain Pump & Filter Trap',
    hindiName: 'ड्रेन पंप / कॉइन ट्रैप',
    cue: 'Small motor housing near the lower outlet hose with a twist-out debris trap.',
  },
  compressor_relay: {
    id: 'compressor_relay',
    title: 'PTC Relay & Overload Protector (OLP)',
    hindiName: 'रिले और ओवरलोड (OLP)',
    cue: 'Clip-on starter block mounted directly on the three compressor pins.',
  },
  ro_membrane: {
    id: 'ro_membrane',
    title: 'RO Membrane Housing & Flow Restrictor',
    hindiName: 'RO मेम्ब्रेन / FR',
    cue: 'Horizontal pressure cylinder with one feed port and two outlet tubes (pure + reject).',
  },
  pcb_board: {
    id: 'pcb_board',
    title: 'Main Control PCB',
    hindiName: 'मेन PCB बोर्ड',
    cue: 'Circuit board with relay cubes, connectors, and conformal coating inside the control box.',
  },
  fan_canopy: {
    id: 'fan_canopy',
    title: 'Ceiling Fan Canopy & Terminal Block',
    hindiName: 'फैन कैनोपी / कनेक्टर',
    cue: 'Upper bell cover hiding the ceiling hook, 2-way connector block, and downrod.',
  },
  ac_filter_coil: {
    id: 'ac_filter_coil',
    title: 'Indoor Filter Mesh & Evaporator Coil',
    hindiName: 'AC फ़िल्टर और कूलिंग कॉइल',
    cue: 'Removable dust mesh sitting in front of aluminium fin rows under the front flap.',
  },
  solar_isolator: {
    id: 'solar_isolator',
    title: 'DC Isolator Switch & MC4 Connectors',
    hindiName: 'सोलर DC आइसोलेटर',
    cue: 'Rotary DC disconnect box between rooftop solar strings and the inverter.',
  },
  generic_part: {
    id: 'generic_part',
    title: 'Appliance Inspection Point',
    hindiName: 'जाँच बिंदु',
    cue: 'Check external nameplate, indicators, wiring entry, and mounting before opening.',
  },
}

function Frame({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 120 84" className="h-20 w-28 shrink-0 rounded-xl border border-line bg-surface-2 p-1" role="img" aria-hidden>
      {children}
    </svg>
  )
}

export function PartDiagramSvg({ id }: { id: PartDiagramId }) {
  switch (id) {
    case 'capacitor':
      return (
        <Frame>
          <rect x="42" y="16" width="36" height="50" rx="6" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <rect x="42" y="24" width="36" height="8" fill="var(--color-accent)" opacity="0.25" />
          <text x="60" y="45" textAnchor="middle" fontSize="8" fontWeight="700" fill="var(--color-ink)">µF</text>
          <path d="M52 16 V7 M68 16 V7" stroke="var(--color-ink)" strokeWidth="2.2" strokeLinecap="round" />
          <circle cx="52" cy="7" r="2.5" fill="var(--color-accent)" />
          <circle cx="68" cy="7" r="2.5" fill="var(--color-accent)" />
          <rect x="52" y="66" width="16" height="7" rx="2" fill="var(--color-ink-3)" />
        </Frame>
      )
    case 'mcb':
      return (
        <Frame>
          <rect x="38" y="8" width="44" height="68" rx="6" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <rect x="48" y="14" width="24" height="7" rx="2" fill="var(--color-ok)" />
          <rect x="49" y="28" width="22" height="36" rx="4" fill="var(--color-bg-2)" stroke="var(--color-line-2)" />
          <rect x="51" y="44" width="18" height="16" rx="3" fill="var(--color-accent)" />
          <text x="60" y="72" textAnchor="middle" fontSize="7" fontWeight="700" fill="var(--color-ink-2)">OFF</text>
        </Frame>
      )
    case 'drain_pump':
      return (
        <Frame>
          <circle cx="48" cy="44" r="20" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <circle cx="48" cy="44" r="8" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeDasharray="3 2" />
          <path d="M68 38 H98 V50 H68" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <path d="M40 24 V12 H56 V24" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <path d="M78 44 H94 M89 40 L94 44 L89 48" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </Frame>
      )
    case 'compressor_relay':
      return (
        <Frame>
          <ellipse cx="48" cy="44" rx="22" ry="26" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <circle cx="48" cy="34" r="3" fill="var(--color-ink)" />
          <circle cx="40" cy="48" r="3" fill="var(--color-ink)" />
          <circle cx="56" cy="48" r="3" fill="var(--color-ink)" />
          <rect x="74" y="26" width="24" height="34" rx="4" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2" />
          <text x="86" y="46" textAnchor="middle" fontSize="7" fontWeight="700" fill="var(--color-ink)">PTC</text>
        </Frame>
      )
    case 'ro_membrane':
      return (
        <Frame>
          <rect x="24" y="26" width="66" height="30" rx="8" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <path d="M10 41 H24" stroke="var(--color-accent)" strokeWidth="2.5" />
          <path d="M90 34 H108 M90 48 H108" stroke="var(--color-ink-2)" strokeWidth="2" />
          <rect x="94" y="44" width="10" height="8" rx="2" fill="var(--color-warn)" />
          <text x="57" y="44" textAnchor="middle" fontSize="8" fontWeight="700" fill="var(--color-ink)">RO</text>
        </Frame>
      )
    case 'pcb_board':
      return (
        <Frame>
          <rect x="20" y="14" width="80" height="56" rx="5" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <rect x="30" y="24" width="22" height="18" rx="2" fill="var(--color-accent)" opacity="0.28" stroke="var(--color-accent)" />
          <rect x="62" y="22" width="16" height="14" rx="2" fill="var(--color-surface-3)" stroke="var(--color-ink-2)" />
          <rect x="82" y="22" width="10" height="24" rx="2" fill="var(--color-surface-3)" stroke="var(--color-ink-2)" />
          <path d="M28 56 H86" stroke="var(--color-ink-3)" strokeWidth="2" strokeDasharray="5 3" />
        </Frame>
      )
    case 'fan_canopy':
      return (
        <Frame>
          <line x1="26" y1="12" x2="94" y2="12" stroke="var(--color-ink-2)" strokeWidth="2.5" />
          <path d="M60 12 V70" stroke="var(--color-ink)" strokeWidth="3" />
          <path d="M42 34 C42 18, 78 18, 78 34 Z" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2" />
          <rect x="52" y="22" width="16" height="7" rx="2" fill="var(--color-surface-3)" stroke="var(--color-ink-2)" />
          <ellipse cx="60" cy="70" rx="24" ry="6" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
        </Frame>
      )
    case 'ac_filter_coil':
      return (
        <Frame>
          <rect x="18" y="14" width="84" height="56" rx="6" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <path d="M26 24 H94 M26 32 H94 M26 40 H94 M26 48 H94 M26 56 H94" stroke="var(--color-accent)" strokeWidth="1.6" />
          <path d="M40 14 V70 M60 14 V70 M80 14 V70" stroke="var(--color-line-2)" strokeWidth="1.2" />
        </Frame>
      )
    case 'solar_isolator':
      return (
        <Frame>
          <rect x="30" y="12" width="60" height="60" rx="7" fill="var(--color-surface)" stroke="var(--color-crit)" strokeWidth="2" />
          <circle cx="60" cy="42" r="16" fill="var(--color-bg-2)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <line x1="49" y1="42" x2="71" y2="42" stroke="var(--color-crit)" strokeWidth="4" strokeLinecap="round" />
          <text x="60" y="23" textAnchor="middle" fontSize="7" fontWeight="700" fill="var(--color-crit)">DC OFF</text>
        </Frame>
      )
    default:
      return (
        <Frame>
          <rect x="24" y="16" width="72" height="52" rx="8" fill="var(--color-surface)" stroke="var(--color-ink-2)" strokeWidth="2" />
          <circle cx="54" cy="40" r="12" fill="none" stroke="var(--color-accent)" strokeWidth="2.5" />
          <line x1="63" y1="49" x2="74" y2="60" stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round" />
        </Frame>
      )
  }
}
