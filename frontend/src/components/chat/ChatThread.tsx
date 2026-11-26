import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Check, Zap, Copy, Download, FileText, Loader2, ThumbsDown, ThumbsUp, Volume2 } from 'lucide-react'
import { Emblem } from '../common/Logo'
import { useApp } from '../../context/AppContext'
import { usePrefs } from '../../context/PrefsContext'
import type { ChatMessage } from '../../types'
import { SourceList } from '../common/SourceList'
import { AuthImage } from '../common/AuthImage'
import { Markdown } from './Markdown'
import { DocChip } from '../composer/Composer'
import { openFile } from '../../utils/openFile'
import { speakable } from '../../utils/text'
import { sessionService } from '../../services'
import { speech, speechSupported } from '../../services/speech'
import { useLanguage, useT } from '../../i18n'

const time = (t: number) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const tool = 'inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink'

function Avatar() {
  return <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface"><Emblem height={18} /></div>
}

function CopyButton({ text }: { text: string }) {
  const t = useT()
  const [ok, setOk] = useState(false)
  const copy = async () => { try { await navigator.clipboard.writeText(speakable(text)); setOk(true); setTimeout(() => setOk(false), 1500) } catch { /* clipboard blocked */ } }
  return <button onClick={copy} aria-label={t('chat.copy')} title={t('chat.copy')} className={tool}>{ok ? <Check size={13} className="text-accent" /> : <Copy size={13} />}<span className="sr-only sm:not-sr-only">{ok ? t('chat.copied') : t('chat.copy')}</span></button>
}

function ReadAloud({ text, id }: { text: string; id: string }) {
  const t = useT()
  const language = useLanguage()
  const { sessionId } = useApp()
  const { voiceURI, rate, aiVoice } = usePrefs()
  if (!speechSupported()) return null
  return <button onClick={() => speech.speak(text, { language, voiceURI, rate, aiVoice, source: sessionId ? { sessionId, messageId: id } : null })} aria-label={t('chat.readAloud')} title={t('chat.readAloud')} className={tool}><Volume2 size={13} /><span className="sr-only sm:not-sr-only">{t('chat.readAloud')}</span></button>
}

/** Thumbs up / down on an AI answer. A thumbs down opens a one-line note for what was wrong. Saved on the server with the message. */
function RateAnswer({ m }: { m: ChatMessage }) {
  const t = useT()
  const { sessionId } = useApp()
  const [value, setValue] = useState<boolean | undefined>(m.helpful)
  const [note, setNote] = useState('')
  const [asking, setAsking] = useState(false)
  const [sent, setSent] = useState(false)
  const [failed, setFailed] = useState(false)
  if (!sessionId) return null
  /** Optimistic: the thumb lights up at once and goes back if the server did not save it. Returns whether it was saved. */
  const save = async (helpful: boolean | null, comment?: string) => {
    const before = value
    setValue(helpful ?? undefined); setFailed(false)
    try { await sessionService.rateAnswer(sessionId, m.id, helpful, comment); return true } catch { setValue(before); setFailed(true); return false }
  }
  const pick = (helpful: boolean) => {
    if (value === helpful) { setAsking(false); void save(null); return }
    setSent(false); setAsking(!helpful); void save(helpful)
  }
  const on = 'bg-surface-2 text-ink'
  return (
    <>
      <button onClick={() => pick(true)} aria-pressed={value === true} aria-label={t('chat.helpful')} title={t('chat.helpful')} className={`${tool} ${value === true ? on : ''}`}><ThumbsUp size={13} className={value === true ? 'text-accent' : ''} /></button>
      <button onClick={() => pick(false)} aria-pressed={value === false} aria-label={t('chat.notHelpful')} title={t('chat.notHelpful')} className={`${tool} ${value === false ? on : ''}`}><ThumbsDown size={13} className={value === false ? 'text-warn' : ''} /></button>
      {sent && !failed && <span className="ml-1 text-accent">{t('chat.thanks')}</span>}
      {failed && <span role="alert" className="ml-1 text-crit">{t('chat.rateFailed')}</span>}
      {asking && (
        <form className="mt-1.5 flex w-full max-w-md items-center gap-2" onSubmit={e => { e.preventDefault(); setAsking(false); void save(false, note.trim()).then(ok => setSent(ok)) }}>
          <input value={note} onChange={e => setNote(e.target.value)} maxLength={500} autoFocus placeholder={t('chat.whatWrong')} aria-label={t('chat.whatWrong')}
            className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[13px] text-ink outline-none focus:border-accent" />
          <button type="submit" className="btn btn-sm">{t('chat.send')}</button>
        </form>
      )}
    </>
  )
}

/** The download card under a "report ready" reply. The PDF is built on the server from this conversation's recorded data. */
function PdfCard() {
  const t = useT()
  const { sessionId, session } = useApp()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const get = async () => {
    if (!sessionId) return
    setBusy(true); setErr(null)
    try { await sessionService.downloadPdf(sessionId, session?.reference) } catch (e) { setErr((e as Error).message || 'Could not create the PDF.') } finally { setBusy(false) }
  }
  return (
    <div className="mt-3 flex max-w-md items-center gap-3 rounded-2xl border border-line bg-surface p-3">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-crit/10 text-crit"><FileText size={20} /></span>
      <span className="min-w-0 flex-1"><span className="block text-sm font-semibold">{t('chat.pdfTitle')}</span><span className="block truncate text-xs text-ink-3">{err ?? t('chat.pdfSub')}</span></span>
      <button onClick={() => void get()} disabled={busy || !sessionId} className="btn btn-primary btn-sm">{busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}{busy ? t('chat.preparing') : t('chat.downloadPdf')}</button>
    </div>
  )
}

// The server adds this sentence to every microwave answer; shown as a red warning instead of a line of text.
const MICROWAVE_HV = /Do not open the microwave\. Its high-voltage capacitor can hold a lethal charge even after unplugging\. Unplug the oven, note the symptom and model number, and hand it to authorised service\.\s*/

function Bubble({ m }: { m: ChatMessage }) {
  if (m.role === 'system') {
    return (
      <div role="status" className="mx-auto flex max-w-xl items-start gap-3 rounded-2xl border border-warn/35 bg-warn/[0.07] px-4 py-3.5 text-sm text-warn">
        <AlertTriangle size={17} className="mt-0.5 shrink-0" />
        <span>
          {m.notice === 'ai_unavailable' ? `AI is not available: ${m.text}` : `The AI could not reply: ${m.text}`} Your message was saved.
          {m.hint && <span className="mt-1.5 block text-xs text-ink-2">Fix: {m.hint}{m.errorCode ? ` (${m.errorCode})` : ''}</span>}
        </span>
      </div>
    )
  }
  const mine = m.role === 'user'
  const raw = m.demo ? (m.text ?? '').replace(/^\s*DEMO SCENARIO \(scripted sample, not live AI\)\.\s*/i, '') : (m.text ?? '')
  const hv = m.role === 'assistant' && MICROWAVE_HV.test(raw)
  const body = hv ? raw.replace(MICROWAVE_HV, '') : raw
  const photos = m.attachments && m.attachments.length > 0 && (
    <div className={`mb-2 flex flex-wrap gap-2 ${mine ? 'justify-end' : ''}`}>{m.attachments.map(a => a.kind === 'document'
      ? <DocChip key={a.id} name={a.name || 'Document'} size={a.size} onOpen={() => void openFile(a).catch(() => undefined)} />
      : a.server
        ? <AuthImage key={a.id} src={a.url} alt="Attached appliance" className="h-32 w-32 overflow-hidden rounded-2xl border border-line" />
        : <img key={a.id} src={a.url} alt="Attached appliance" className="h-32 w-32 rounded-2xl border border-line object-cover" />)}</div>
  )
  if (mine) {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }} className="flex justify-end">
        <div className="flex max-w-[85%] flex-col items-end sm:max-w-[75%]">
          {photos}
          {m.text && <div className="whitespace-pre-wrap rounded-[20px] rounded-br-md bg-surface-2 px-4 py-2.5 text-[15px] leading-relaxed text-ink">{m.text}</div>}
          <span className="mt-1 px-1 text-[12px] text-ink-3">{time(m.at)}</span>
        </div>
      </motion.div>
    )
  }
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} className="flex gap-3">
      <Avatar />
      <div className="min-w-0 flex-1 pt-0.5">
        {m.demo && <span className="mb-2 inline-block rounded-full border border-warn/40 bg-warn/[0.08] px-2 py-px text-[12px] font-medium text-warn">Demo: scripted sample, not live AI</span>}
        {photos}
        {/* the badge above already says it is scripted; the same words again at the top of the reply are noise */}
        {hv && (
          <div role="alert" className="mb-3 flex gap-3 rounded-xl border border-crit/50 bg-crit/[0.07] p-3.5">
            <Zap size={18} className="mt-0.5 shrink-0 text-crit" aria-hidden />
            <div className="text-sm leading-relaxed"><p className="font-semibold text-crit">Do not open the microwave</p>
              <p className="text-ink-2">The high-voltage capacitor can hold a lethal charge even after unplugging. Unplug it, note the model and symptom, and hand it to authorised service.</p></div>
          </div>
        )}
        {body && <Markdown text={body} sources={m.sources} />}
        {m.action === 'pdf_report' && <PdfCard />}
        {m.sources && m.sources.length > 0 && <SourceList sources={m.sources} />}
        <div className="mt-1.5 flex flex-wrap items-center gap-0.5 text-[12.5px] text-ink-3">
          {m.text && m.action !== 'pdf_report' && <ReadAloud text={m.text} id={m.id} />}
          {m.text && <CopyButton text={m.text} />}
          {m.aiGenerated && !m.demo && m.action !== 'pdf_report' && <RateAnswer m={m} />}
          <span className="ml-1.5">{time(m.at)}</span>
        </div>
      </div>
    </motion.div>
  )
}

function ThinkingLabel({ progress }: { progress: string | null }) {
  const t = useT()
  const [s, setS] = useState(0)
  useEffect(() => { const id = setInterval(() => setS(x => x + 1), 1000); return () => clearInterval(id) }, [])
  if (progress) return <span className="text-sm"><span className="text-shimmer font-medium">{progress}...</span></span>
  // Retrieval takes milliseconds; nearly all of the wait is the AI model. After ~12 s the server also asks the backup model.
  const phase = s < 2 ? t('think.check') : s < 12 ? t('think.write') : t('think.slow')
  return <span className="text-sm tabular-nums"><span className="text-shimmer font-medium">{phase}…</span> <span className="text-ink-3">{s}s</span></span>
}

export function ChatThread() {
  const { messages, thinking, progress, error } = useApp()
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages.length, thinking])
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 pb-4 pt-6 md:px-6" role="log" aria-live="polite" aria-label="Conversation">
      {messages.map(m => <Bubble key={m.id} m={m} />)}
      {thinking && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3" aria-label="FixSaathi is thinking">
          <Avatar />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 py-1.5">
              <span className="flex items-center gap-1">{[0, 1, 2].map(i => <span key={i} className="typing-dot h-1.5 w-1.5 rounded-full bg-accent" style={{ animationDelay: `${i * 0.15}s` }} />)}</span>
              <ThinkingLabel progress={progress} />
            </div>
            <div className="mt-2 space-y-2.5" aria-hidden><div className="skeleton h-3.5 w-11/12" /><div className="skeleton h-3.5 w-4/5" /><div className="skeleton h-3.5 w-3/5" /></div>
          </div>
        </motion.div>
      )}
      {error && <p role="alert" className="rounded-2xl border border-crit/40 bg-crit/10 px-4 py-3 text-sm text-crit">{error}</p>}
      <div ref={end} />
    </div>
  )
}
