import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, CheckCircle2, Cpu, Edit3, Loader2, Search } from 'lucide-react'
import type { NameplateData, NameplateResponse, NameplateRetrieval } from '../../types'

const APPLIANCE_OPTIONS = [
  ['', 'Keep current / unknown'],
  ['split_ac', 'Split AC'],
  ['washing_machine', 'Washing machine'],
  ['refrigerator', 'Refrigerator'],
  ['ceiling_fan', 'Ceiling fan'],
  ['microwave_oven', 'Microwave oven'],
  ['water_purifier', 'Water purifier'],
  ['mcb_electrical', 'MCB / electrical'],
  ['rooftop_solar', 'Rooftop solar'],
] as const

interface Props {
  initialNameplate?: NameplateData | null
  response: NameplateResponse | null
  sessionAppliance: string
  canEdit: boolean
  busy: boolean
  onSave: (patch: { appliance_type?: string | null; brand?: string | null; model?: string | null; error_code?: string | null; serial_number?: string | null }) => Promise<void>
}

export function NameplateCard({ initialNameplate, response, sessionAppliance, canEdit, busy, onSave }: Props) {
  const active: NameplateData | null = response?.extracted ?? initialNameplate ?? null
  const retrieval: NameplateRetrieval | null = response?.retrieval ?? null
  const aiError = response && response.status !== 'ok' ? response.ai_error : null

  const [manualOpen, setManualOpen] = useState(false)
  const [brand, setBrand] = useState(active?.brand ?? '')
  const [model, setModel] = useState(active?.model ?? '')
  const [errorCode, setErrorCode] = useState(active?.error_code ?? '')
  const [serialNumber, setSerialNumber] = useState(active?.serial_number ?? '')
  const [applianceType, setApplianceType] = useState(active?.appliance_type ?? (sessionAppliance !== 'unknown' ? sessionAppliance : ''))

  useEffect(() => {
    setBrand(active?.brand ?? '')
    setModel(active?.model ?? '')
    setErrorCode(active?.error_code ?? '')
    setSerialNumber(active?.serial_number ?? '')
    setApplianceType(active?.appliance_type ?? (sessionAppliance !== 'unknown' ? sessionAppliance : ''))
  }, [active, sessionAppliance])

  useEffect(() => {
    if (aiError) setManualOpen(true)
  }, [aiError])

  const showForm = !!active || !!aiError || manualOpen

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    await onSave({
      brand: brand.trim() || null,
      model: model.trim() || null,
      error_code: errorCode.trim() || null,
      serial_number: serialNumber.trim() || null,
      appliance_type: applianceType ? applianceType : null,
    })
  }

  if (!showForm) {
    if (!canEdit) return null
    return (
      <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-line bg-surface-2/40 px-3.5 py-2.5 text-xs text-ink-2">
        <span>Have a rating label or error code? Read it from a photo above or enter it manually.</span>
        <button type="button" onClick={() => setManualOpen(true)} className="btn btn-sm shrink-0">
          <Edit3 size={13} />Enter nameplate
        </button>
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-2xl border border-line bg-surface-2/45 p-4 text-sm" role="region" aria-label="Nameplate and error display">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Cpu size={16} className="text-accent" aria-hidden />
          <p className="font-semibold text-ink">Nameplate &amp; error display</p>
        </div>
        {active && (
          <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${active.verified_by_technician ? 'border-accent/40 bg-accent/10 text-accent' : 'border-teal/40 bg-teal/10 text-teal'}`}>
            {active.verified_by_technician && <CheckCircle2 size={12} aria-hidden />}
            {active.verified_by_technician ? 'Checked by technician' : 'AI estimate · check & edit'}
          </span>
        )}
      </div>

      {aiError && (
        <div role="alert" className="mt-3 flex items-start gap-2.5 rounded-xl border border-warn/45 bg-warn/10 px-3.5 py-2.5 text-xs leading-relaxed text-ink">
          <AlertTriangle size={15} className="mt-0.5 shrink-0 text-warn" aria-hidden />
          <div>
            <p className="font-semibold text-warn">Could not read photo with Gemini Vision ({aiError.code})</p>
            <p className="text-ink-2">{aiError.message}</p>
            {aiError.hint && <p className="mt-0.5 text-ink-2">{aiError.hint}</p>}
          </div>
        </div>
      )}

      {active && !active.readable && (
        <p className="mt-2.5 rounded-xl border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-ink-2">
          Photo was not clear enough to read automatically{active.notes ? `: ${active.notes}` : '.'} Enter what you see on the label below.
        </p>
      )}

      {active?.raw_text && (
        <p className="mt-2.5 rounded-lg border border-line bg-bg/60 px-3 py-1.5 font-mono text-[11px] text-ink-2" title="Raw text read from image">
          Visible text: {active.raw_text}
        </p>
      )}

      <form onSubmit={e => void submit(e)} className="mt-3 grid gap-2.5 sm:grid-cols-2">
        <div>
          <label htmlFor="np-brand" className="mb-1 block text-xs font-medium text-ink-2">Brand</label>
          <input id="np-brand" value={brand} onChange={e => setBrand(e.target.value)} disabled={!canEdit || busy} placeholder="e.g. LG, Voltas, IFB" className="field !min-h-[44px] text-sm" />
        </div>
        <div>
          <label htmlFor="np-model" className="mb-1 block text-xs font-medium text-ink-2">Model</label>
          <input id="np-model" value={model} onChange={e => setModel(e.target.value)} disabled={!canEdit || busy} placeholder="e.g. LS-Q18YNZA" className="field !min-h-[44px] text-sm" />
        </div>
        <div>
          <label htmlFor="np-code" className="mb-1 block text-xs font-medium text-ink-2">Error code</label>
          <input id="np-code" value={errorCode} onChange={e => setErrorCode(e.target.value)} disabled={!canEdit || busy} placeholder="e.g. CH38, E4, UE" className="field !min-h-[44px] text-sm font-mono uppercase" />
        </div>
        <div>
          <label htmlFor="np-app" className="mb-1 block text-xs font-medium text-ink-2">Appliance</label>
          <select id="np-app" value={applianceType} onChange={e => setApplianceType(e.target.value)} disabled={!canEdit || busy} className="field !min-h-[44px] text-sm">
            {APPLIANCE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        {serialNumber && (
          <div className="sm:col-span-2">
            <label htmlFor="np-serial" className="mb-1 block text-xs font-medium text-ink-2">Serial number</label>
            <input id="np-serial" value={serialNumber} onChange={e => setSerialNumber(e.target.value)} disabled={!canEdit || busy} className="field !min-h-[44px] text-sm font-mono" />
          </div>
        )}
        {canEdit && (
          <div className="flex flex-wrap items-center gap-2 pt-1 sm:col-span-2">
            <button type="submit" disabled={busy} className="btn btn-primary btn-sm !min-h-[44px]">
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              Save &amp; search records
            </button>
            <span className="text-xs text-ink-3">Saved brand, model and code ground the diagnosis.</span>
          </div>
        )}
      </form>

      {retrieval && (
        <div className="mt-3.5 border-t border-line pt-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold text-ink-2">Matching repair records ({retrieval.hits.length})</p>
            <span className="text-[11px] text-ink-3">Coverage: {retrieval.coverage}</span>
          </div>
          {retrieval.error_codes_unknown.length > 0 && (
            <p className="mt-1.5 text-xs text-warn">
              No repair record matches code {retrieval.error_codes_unknown.join(', ')} yet. Check spelling or re-run diagnosis with a symptom description.
            </p>
          )}
          {retrieval.hits.length === 0 ? (
            <p className="mt-1.5 text-xs text-ink-3">No matching records found for those nameplate details yet.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {retrieval.hits.map(h => (
                <li key={h.record_id} className="rounded-xl border border-line bg-surface px-3 py-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-1.5">
                    <span className="font-semibold text-ink">{h.title}</span>
                    <span className="rounded-full border border-line bg-surface-2 px-2 py-px font-mono text-[10px] text-ink-3">{h.record_id}</span>
                  </div>
                  {h.possible_faults.length > 0 && (
                    <p className="mt-1 text-ink-2">Possible causes: {h.possible_faults.join('; ')}</p>
                  )}
                  <p className="mt-0.5 text-[11px] text-ink-3">Source: {h.source_name} · {h.match.replace('_', ' ')}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
