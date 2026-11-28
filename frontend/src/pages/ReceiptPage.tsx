import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Check, Circle, Copy, ExternalLink, Lock, Printer, ShieldAlert, ShieldCheck, Wrench } from 'lucide-react'
import { Emblem, Wordmark } from '../components/common/Logo'
import { Skeleton } from '../components/common/ui'
import { apiBase, type ApiError } from '../services/api'
import { receiptService, type CustomerReceiptResponse } from '../services'

export default function ReceiptPage() {
  const { id = '' } = useParams()
  const [lang, setLang] = useState<'hi' | 'en'>('hi')
  const [copied, setCopied] = useState(false)
  const [data, setData] = useState<CustomerReceiptResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errInfo, setErrInfo] = useState<{ expired: boolean; message: string } | null>(null)

  const load = useCallback(() => {
    let live = true
    setLoading(true); setErrInfo(null)
    receiptService.getPublic(id)
      .then(d => { if (live) { setData(d); setLoading(false) } })
      .catch(e => {
        if (!live) return
        const a = e as Partial<ApiError>
        const msg = a?.message || 'Could not load this safety receipt.'
        setErrInfo({ expired: a?.status === 410 || msg.toLowerCase().includes('expired'), message: msg })
        setLoading(false)
      })
    return () => { live = false }
  }, [id])

  useEffect(() => load(), [load])

  const hi = lang === 'hi'
  const shareUrl = typeof window !== 'undefined' ? window.location.href : `/receipt/${id}`

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch { /* ignore clipboard errors in restricted contexts */ }
  }

  const r = data?.receipt
  const qrSrc = data ? `${apiBase}${data.qr_url}` : ''

  return (
    <div className="min-h-dvh bg-bg text-ink">
      <header className="border-b border-line bg-surface/85 backdrop-blur-sm print:hidden">
        <div className="mx-auto flex max-w-lg items-center justify-between gap-2 px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <Emblem height={30} />
            <Wordmark height={15} />
          </Link>
          <div className="inline-flex rounded-xl border border-line bg-bg/60 p-0.5" role="group" aria-label="Language">
            <button type="button" onClick={() => setLang('hi')}
              className={`min-h-[38px] rounded-lg px-3 text-xs font-semibold transition-colors ${hi ? 'bg-surface text-ink shadow-[var(--shadow-card)] ring-1 ring-line-2' : 'text-ink-2 hover:text-ink'}`}>
              हिंदी
            </button>
            <button type="button" onClick={() => setLang('en')}
              className={`min-h-[38px] rounded-lg px-3 text-xs font-semibold transition-colors ${!hi ? 'bg-surface text-ink shadow-[var(--shadow-card)] ring-1 ring-line-2' : 'text-ink-2 hover:text-ink'}`}>
              English
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-lg space-y-4 px-4 py-5">
        {loading && <div className="space-y-3"><Skeleton className="h-24" /><Skeleton className="h-64" /></div>}

        {errInfo && (
          <div role="alert" className="card card-pad space-y-3 text-center">
            <ShieldAlert size={28} className="mx-auto text-warn" aria-hidden />
            <h1 className="font-display text-lg text-ink">
              {errInfo.expired
                ? (hi ? 'यह सुरक्षा रसीद समाप्त हो चुकी है' : 'This safety receipt has expired')
                : (hi ? 'सुरक्षा रसीद नहीं मिली' : 'Safety receipt not found')}
            </h1>
            <p className="text-xs text-ink-2">{errInfo.message}</p>
            <button type="button" onClick={load} className="btn btn-sm">{hi ? 'फिर से कोशिश करें' : 'Try again'}</button>
          </div>
        )}

        {data && r && (
          <article className="card card-pad space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line pb-4">
              <div>
                <p className="section-label">{hi ? 'ग्राहक सुरक्षा रसीद' : 'Customer Safety Receipt'}</p>
                <h1 className="font-display mt-1 text-xl text-ink">
                  {hi ? r.appliance_hi : r.appliance_en}
                </h1>
                {r.unit_label && <p className="mt-0.5 text-xs font-medium text-teal">{r.unit_label}</p>}
              </div>
              <span className="num rounded-full border border-line bg-surface-2 px-2.5 py-1 text-xs text-ink-2">
                {r.session_reference}
              </span>
            </div>

            {/* Safety lock status banner */}
            <section aria-label={hi ? 'सुरक्षा स्थिति' : 'Safety status'}
              className={`rounded-xl border p-3.5 ${r.safety_status.unlocked ? 'border-ok/40 bg-ok/[0.06]' : 'border-crit/40 bg-crit/[0.06]'}`}>
              <div className="flex items-center gap-2 font-semibold text-sm">
                {r.safety_status.unlocked
                  ? <ShieldCheck size={17} className="shrink-0 text-ok" aria-hidden />
                  : <Lock size={17} className="shrink-0 text-crit" aria-hidden />}
                <span>
                  {r.safety_status.unlocked
                    ? (hi ? 'सुरक्षा जांच पूरी (पावर बंद की पुष्टि)' : 'Safety checks recorded (isolation stated)')
                    : (hi ? 'पावर लॉक सक्रिय रहा (बिना बिजली का काम)' : 'Power safety lock remained active')}
                </span>
              </div>
              <ul className="mt-2.5 space-y-1.5 text-xs">
                <li className="flex items-center gap-2">
                  {r.safety_status.power_off_confirmed ? <Check size={14} className="text-ok" aria-hidden /> : <Circle size={12} className="text-ink-3" aria-hidden />}
                  <span>{hi ? 'टेक्नीशियन ने MCB बंद करने की पुष्टि की' : 'Technician stated MCB / mains switched off'}</span>
                </li>
                <li className="flex items-center gap-2">
                  {r.safety_status.tester_checked ? <Check size={14} className="text-ok" aria-hidden /> : <Circle size={12} className="text-ink-3" aria-hidden />}
                  <span>{hi ? 'अपने टेस्टर से सप्लाई जांच की पुष्टि की' : 'Technician stated circuit checked with own tester'}</span>
                </li>
              </ul>
              <p className="mt-2.5 text-[11px] leading-relaxed text-ink-3">
                {hi ? r.safety_status.disclaimer_hi : r.safety_status.disclaimer_en}
              </p>
            </section>

            <section className="space-y-3 text-sm">
              <div>
                <p className="text-xs font-semibold text-ink-3">{hi ? 'समस्या' : 'Reported issue'}</p>
                <p className="mt-0.5 text-ink">{r.issue}</p>
              </div>

              <div>
                <p className="text-xs font-semibold text-ink-3">{hi ? 'की गई जांच और काम' : 'Checks & steps completed'}</p>
                {r.checks_done.length > 0 ? (
                  <ol className="mt-1 list-decimal space-y-1 pl-5 text-ink-2">
                    {r.checks_done.map((step, i) => <li key={i}>{step}</li>)}
                  </ol>
                ) : (
                  <p className="mt-0.5 text-xs text-ink-3">{hi ? 'अभी कोई पूरा स्टेप दर्ज नहीं है।' : 'No completed repair steps recorded.'}</p>
                )}
              </div>

              <div>
                <p className="text-xs font-semibold text-ink-3">{hi ? 'जांचे गए पुर्जे' : 'Parts checked / identified'}</p>
                {r.parts.length > 0 ? (
                  <ul className="mt-1 flex flex-wrap gap-1.5">
                    {r.parts.map((part, i) => (
                      <li key={i} className="inline-flex items-center gap-1 rounded-full border border-line bg-surface-2 px-2.5 py-0.5 text-xs text-ink">
                        <Wrench size={11} aria-hidden />{part}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-0.5 text-xs text-ink-3">{hi ? 'कोई अलग पुर्जा दर्ज नहीं' : 'None recorded'}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 border-t border-line pt-3 text-xs">
                <div>
                  <p className="text-ink-3">{hi ? 'टेक्नीशियन' : 'Technician'}</p>
                  <p className="mt-0.5 font-semibold text-ink">{r.technician_name}</p>
                </div>
                <div>
                  <p className="text-ink-3">{hi ? 'जारी दिनांक' : 'Issued'}</p>
                  <p className="num mt-0.5 font-medium text-ink">{new Date(r.issued_at).toLocaleDateString()}</p>
                </div>
              </div>
            </section>

            {/* Scannable QR Code */}
            <section className="flex flex-col items-center gap-2 rounded-xl border border-line bg-surface-2/40 p-4 text-center">
              <img
                src={qrSrc}
                alt={hi ? 'सुरक्षा रसीद का QR कोड' : 'Safety receipt QR code'}
                className="h-36 w-36 rounded-lg border border-line bg-white p-1.5"
              />
              <p className="text-xs text-ink-2">
                {hi ? 'इस रसीद को फोन में खोलने के लिए QR कोड स्कैन करें' : 'Scan QR code to view this safety receipt on any phone'}
              </p>
              <p className="text-[11px] text-ink-3">
                {hi ? 'इसमें ग्राहक का कोई निजी डेटा (फ़ोन, पता, ईमेल) सेव नहीं है।' : 'Zero customer personal data (phone, address, email) is stored.'}{' '}
                {hi ? `वैधता समाप्त: ${new Date(data.expires_at).toLocaleDateString()}` : `Expires: ${new Date(data.expires_at).toLocaleDateString()}`}
              </p>
            </section>

            <div className="flex flex-wrap gap-2 print:hidden">
              <button type="button" onClick={() => void copyLink()} className="btn flex-1">
                {copied ? <Check size={15} className="text-accent" /> : <Copy size={15} />}
                {copied ? (hi ? 'लिंक कॉपी हुआ' : 'Link copied') : (hi ? 'रसीद लिंक कॉपी करें' : 'Copy receipt link')}
              </button>
              <button type="button" onClick={() => window.print()} className="btn">
                <Printer size={15} />{hi ? 'प्रिंट' : 'Print'}
              </button>
            </div>
          </article>
        )}

        <p className="text-center text-xs text-ink-3 print:hidden">
          <Link to="/evaluation" className="inline-flex items-center gap-1 hover:text-ink hover:underline">
            FixSaathi Safety Verification <ExternalLink size={11} />
          </Link>
        </p>
      </main>
    </div>
  )
}
