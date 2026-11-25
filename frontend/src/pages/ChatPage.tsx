import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, Loader2, Lock, ShieldCheck, Wrench } from 'lucide-react'
import { ChatThread } from '../components/chat/ChatThread'
import { Composer } from '../components/composer/Composer'
import { Emblem } from '../components/common/Logo'
import { useApp } from '../context/AppContext'
import { usePrefs } from '../context/PrefsContext'
import { repairService, sessionService } from '../services'
import { speech } from '../services/speech'
import { suggestions } from '../constants/prompts'
import { useLanguage, useT } from '../i18n'

export default function ChatPage() {
  const { id } = useParams()
  const nav = useNavigate()
  const t = useT()
  const language = useLanguage()
  const { messages, send, thinking, sessionId, session, openSession, openError, freshReply } = useApp()
  const { speaker, voiceURI, rate, aiVoice } = usePrefs()
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfErr, setPdfErr] = useState<string | null>(null)

  // The URL decides which conversation is open, so a refresh, a bookmark or the back button reopens the same chat.
  const current = useRef(sessionId)
  useEffect(() => { current.current = sessionId }, [sessionId])
  useEffect(() => { if (id && id !== current.current) { speech.stop(); void openSession(id) } }, [id, openSession])
  // A brand-new chat gets its own address as soon as the server creates it.
  useEffect(() => { if (!id && sessionId) nav(`/chat/${sessionId}`, { replace: true }) }, [id, sessionId, nav])

  // A reply is read aloud by itself only when it answers a voice message and the speaker is on. Typed messages get text
  // only, whatever the speaker setting; replies loaded from history are never spoken. Read aloud is always on request.
  const spoken = useRef<string | null>(null)
  useEffect(() => {
    if (!freshReply || spoken.current === freshReply.id) return
    spoken.current = freshReply.id
    if (freshReply.channel !== 'voice' || !speaker || freshReply.action === 'pdf_report' || !sessionId) return
    speech.speak(freshReply.text, { language, voiceURI, rate, aiVoice, source: { sessionId, messageId: freshReply.id } })
  }, [freshReply, speaker, language, voiceURI, rate, aiVoice, sessionId])
  useEffect(() => () => speech.stop(), [])

  // The power state travels with the conversation: the header shows whether power steps are locked, refreshed after each reply.
  const [unlocked, setUnlocked] = useState<boolean | null>(null)
  const replies = messages.filter(m => m.role === 'assistant').length
  useEffect(() => {
    if (!sessionId) return
    let live = true
    repairService.safety(sessionId).then(st => { if (live) setUnlocked(st.unlocked) }).catch(() => { if (live) setUnlocked(null) })
    return () => { live = false }
  }, [sessionId, replies])

  const pdf = async () => {
    if (!sessionId) return
    setPdfBusy(true); setPdfErr(null)
    try { await sessionService.downloadPdf(sessionId, session?.reference) } catch (e) { setPdfErr((e as Error).message) } finally { setPdfBusy(false) }
  }

  if (openError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="max-w-sm text-ink-2">{openError === 'not_found' ? t('chat.notFound') : openError}</p>
        <Link to="/" className="btn">{t('chat.backHome')}</Link>
      </div>
    )
  }
  const loading = !!id && !session && messages.length === 0 && !thinking
  const empty = !id && messages.length === 0 && !thinking
  const title = session?.title || messages.find(m => m.role === 'user' && m.text)?.text || t('nav.newChat')

  return (
    <div className="flex min-h-full flex-col">
      {(sessionId || id) && (
        <div className="glass sticky top-0 z-10 border-b border-line">
          <div className="mx-auto flex w-full max-w-3xl items-center gap-2 px-4 py-2 md:px-6">
            <h1 className="min-w-0 flex-1 truncate text-[15px] font-semibold tracking-tight" title={title}>{loading ? <span className="skeleton inline-block h-4 w-48 align-middle" /> : title}</h1>
            {sessionId && <>
              {unlocked !== null && (
                <Link to={`/session/${sessionId}#safety`} title={unlocked ? 'Safety statements recorded: power steps are released' : 'Power steps are locked until you record both safety statements'}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${unlocked ? 'border-ok/35 text-ok hover:bg-ok/10' : 'border-crit/35 text-crit hover:bg-crit/10'}`}>
                  {unlocked ? <ShieldCheck size={13} aria-hidden /> : <Lock size={13} aria-hidden />}<span className="hidden sm:inline">{unlocked ? 'Isolated' : 'Power steps locked'}</span><span className="sr-only sm:hidden">{unlocked ? 'Isolated' : 'Power steps locked'}</span>
                </Link>
              )}
              <button onClick={() => void pdf()} disabled={pdfBusy} className="btn btn-ghost btn-sm" title={t('chat.downloadPdf')}>{pdfBusy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}<span className="hidden sm:inline">PDF</span></button>
              <button onClick={() => nav(`/session/${sessionId}`)} className="btn btn-sm" title={t('chat.workspace')}><Wrench size={14} /><span className="hidden sm:inline">{t('chat.workspace')}</span></button>
            </>}
          </div>
          {pdfErr && <p role="alert" className="mx-auto max-w-3xl px-4 pb-2 text-xs text-crit md:px-6">{pdfErr}</p>}
        </div>
      )}

      <div className="flex flex-1 flex-col">
        {empty ? (
          <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-5 px-4 py-12 text-center">
            <Emblem height={52} />
            <div>
              <h1 className="font-display text-2xl md:text-[30px]">{t('chat.emptyTitle')}</h1>
              <p className="mt-2 text-ink-2">{t('chat.emptySub')}</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">{suggestions.map(s => <button key={s.key} onClick={() => void send(s.prompt, [], s.appliance)} className="chip">{t(s.key)}</button>)}</div>
          </div>
        ) : loading ? (
          <div className="mx-auto w-full max-w-3xl space-y-6 px-4 pt-10 md:px-6"><div className="skeleton ml-auto h-10 w-2/3" /><div className="skeleton h-24 w-5/6" /><div className="skeleton ml-auto h-10 w-1/2" /></div>
        ) : <ChatThread />}
      </div>

      <div className="sticky bottom-0 bg-gradient-to-t from-bg via-bg to-transparent px-4 pb-3 pt-3" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
        <div className="mx-auto w-full max-w-3xl">
          <Composer compact disabled={thinking || loading || session?.status === 'completed' || session?.status === 'cancelled'} onSend={(text, a, channel) => void send(text, a, undefined, channel)} />
          <p className="mt-2 text-center text-[11px] text-ink-3">{session && (session.status === 'completed' || session.status === 'cancelled') ? 'This repair session is closed. Start a new chat to continue.' : t('chat.disclaimer')}</p>
        </div>
      </div>
    </div>
  )
}
