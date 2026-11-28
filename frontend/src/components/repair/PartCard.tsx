import { PART_SPECS, PartDiagramSvg, type PartDiagramId } from './PartDiagrams'

export function matchPartDiagram(text: string, appliance?: string): PartDiagramId {
  const t = text.toLowerCase()
  if (/capacitor|condenser|µf|uf\b|कैपेसिटर/.test(t)) return 'capacitor'
  if (/dc isolator|mc4|solar|dc string|सोलर/.test(t) || appliance === 'rooftop_solar') return 'solar_isolator'
  if (/\bmcb\b|isolator|breaker|tester|trip|बिजली बंद/.test(t)) return 'mcb'
  if (/drain|pump|filter trap|coin trap|impeller|पंप|ड्रेन/.test(t)) return 'drain_pump'
  if (/ptc|overload|olp|relay|compressor|कंप्रेसर|रिले/.test(t)) return 'compressor_relay'
  if (/membrane|restrictor|ro |purifier|tds|फ़िल्टर|मेम्ब्रेन/.test(t) || appliance === 'water_purifier') return 'ro_membrane'
  if (/pcb|control board|module|circuit board|बोर्ड/.test(t)) return 'pcb_board'
  if (/canopy|hook|downrod|ceiling|कैनोपी|पंखा/.test(t) || appliance === 'ceiling_fan') return 'fan_canopy'
  if (/filter|coil|fins|evaporator|indoor unit|फ़िल्टर|कॉइल/.test(t) || appliance === 'split_ac') return 'ac_filter_coil'
  return 'generic_part'
}

/** Original FixSaathi SVG schematic card for a repair step, clearly labelled as a diagram rather than a photo. */
export function PartCard({ title, instruction, appliance }: { title: string; instruction?: string | null; appliance?: string }) {
  const id = matchPartDiagram(`${title} ${instruction ?? ''}`, appliance)
  const spec = PART_SPECS[id]
  return (
    <div className="mt-3 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 sm:flex-row sm:items-center">
      <PartDiagramSvg id={id} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-ink">
          {spec.title} <span className="font-normal text-ink-3">· {spec.hindiName}</span>
        </p>
        <p className="mt-0.5 text-xs leading-relaxed text-ink-2">{spec.cue}</p>
        <p className="mt-1 text-[11px] font-medium text-ink-3">Schematic diagram (FixSaathi SVG) — not a photo of your unit</p>
      </div>
    </div>
  )
}
