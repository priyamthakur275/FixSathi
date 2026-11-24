import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ApiError } from '../services/api'
import { chatService, fileService, sessionService } from '../services'
import { useMaybeAuth } from './AuthContext'
import type { Attachment, ChatMessage, MessageFile, RepairSession, ServerMessage, SourceRef } from '../types'

interface Ctx {
  collapsed: boolean
  toggleCollapsed: () => void
  sessionId: string | null
  /** The open conversation's session (title, appliance, status), once it exists on the server. */
  session: RepairSession | null
  messages: ChatMessage[]
  thinking: boolean
  /** Shown while files upload before the message is sent, e.g. "Uploading 2 of 3: manual.pdf". */
  progress: string | null
  /** A message that could not be sent, handed back to whichever composer is on screen. */
  draft: { text: string; attachments: Attachment[] } | null
  clearDraft: () => void
  error: string | null
  /** Set when opening a conversation fails (deleted, not yours, offline). */
  openError: string | null
  /** The assistant reply that just arrived in this tab (not replies loaded from history): the one to read aloud. */
  freshReply: ChatMessage | null
  sessionsVersion: number
  refreshSessions: () => void
  /** Resolves false when nothing was sent (e.g. an upload failed), so the composer can restore the draft. */
  send: (text: string, attachments?: Attachment[], appliance?: string, channel?: 'text' | 'voice') => Promise<boolean>
  openSession: (id: string) => Promise<void>
  newSession: () => void
  setSessionTitle: (id: string, title: string) => void
}
const AppCtx = createContext<Ctx | null>(null)
const uid = () => Math.random().toString(36).slice(2, 10)

export const toChat = (m: ServerMessage): ChatMessage => ({
  id: m.id, role: m.role, text: m.message, at: new Date(m.created_at).getTime(), aiGenerated: m.meta?.ai_generated === true, demo: m.meta?.demo === true && m.role === 'assistant',
  sources: (m.meta?.sources as SourceRef[] | undefined) ?? [],
  action: m.meta?.action === 'pdf_report' ? 'pdf_report' : undefined,
  channel: m.meta?.channel === 'voice' ? 'voice' : 'text',
  helpful: typeof (m.meta?.feedback as { helpful?: unknown } | undefined)?.helpful === 'boolean' ? (m.meta.feedback as { helpful: boolean }).helpful : undefined,
  // Files saved with the message: loaded through the authenticated media endpoint when a session is reopened.
  attachments: serverFiles(m),
})

function serverFiles(m: ServerMessage): MessageFile[] {
  const rich = m.meta?.attachments as { id: string; kind?: 'image' | 'document'; name?: string; size?: number; mime?: string; pages?: number }[] | undefined
  if (rich?.length) return rich.map(f => ({ ...f, url: `/api/v1/media/${f.id}`, server: true, name: f.name ?? undefined }))
  return ((m.meta?.media_ids as string[] | undefined) ?? []).map(id => ({ id, url: `/api/v1/media/${id}`, server: true, kind: 'image' as const }))
}

export function AppProvider({ children }: { children: ReactNode }) {
  // Tablets get the slim sidebar by default so the chat has room; the user can still expand it.
  const [collapsed, setCollapsed] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 768 && window.innerWidth < 1024)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [session, setSession] = useState<RepairSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [thinking, setThinking] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [draft, setDraft] = useState<{ text: string; attachments: Attachment[] } | null>(null)
  const clearDraft = useCallback(() => setDraft(null), [])
  const [error, setError] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)
  const [freshReply, setFreshReply] = useState<ChatMessage | null>(null)
  const [sessionsVersion, setSessionsVersion] = useState(0)
  const refreshSessions = useCallback(() => setSessionsVersion(v => v + 1), [])
  const busy = useRef(false)
  const sid = useRef<string | null>(null)
  // Every conversation switch gets a new number. A reply that arrives after the technician moved to another chat is saved on the
  // server as usual, but never shown in, or spoken over, the chat that is now open.
  const conv = useRef(0)

  const reset = useCallback(() => {
    conv.current++; busy.current = false; sid.current = null
    setSessionId(null); setSession(null); setMessages([]); setThinking(false); setProgress(null); setError(null); setOpenError(null); setFreshReply(null)
  }, [])

  const openSession = useCallback(async (id: string) => {
    reset()
    const mine = conv.current
    sid.current = id; setSessionId(id)
    try {
      const [s, history] = await Promise.all([sessionService.get(id), chatService.history(id)])
      if (conv.current !== mine) return
      setSession(s); setMessages(history.items.map(toChat))
    } catch (e) {
      if (conv.current === mine) setOpenError((e as ApiError).status === 404 ? 'not_found' : (e as ApiError).message)
    }
  }, [reset])

  const send = useCallback(async (text: string, attachments: Attachment[] = [], appliance?: string, channel: 'text' | 'voice' = 'text'): Promise<boolean> => {
    if (busy.current || (!text.trim() && attachments.length === 0)) return false
    const mine = conv.current
    const live = () => conv.current === mine
    busy.current = true; setError(null)
    const localId = uid()
    setMessages(m => [...m, { id: localId, role: 'user', text: text.trim(), at: Date.now(),
      attachments: attachments.map(a => ({ id: a.id, url: a.url, kind: a.kind, name: a.name, size: a.size })) }])
    setThinking(true)
    let stage = 'session'
    let target = sid.current
    try {
      if (!target) {
        // A photo-only first message gets a provisional title; the server renames the chat from the first description.
        const s = await sessionService.create(text.trim(), appliance)
        target = s.id
        if (live()) { sid.current = s.id; setSessionId(s.id); setSession(s) }
        setSessionsVersion(v => v + 1)
      }
      stage = 'upload'
      const ids: string[] = []
      for (const [i, a] of attachments.entries()) {
        if (live()) setProgress(attachments.length > 1 ? `Uploading ${i + 1} of ${attachments.length}: ${a.name}` : `Uploading ${a.name}`)
        try { ids.push((await fileService.upload(target, a.file, a.source === 'camera' ? 'capture' : 'upload', a.name)).id) }
        catch (e) { throw new Error(`Could not upload “${a.name}”: ${(e as ApiError).message}`) }
      }
      if (live()) setProgress(null)
      stage = 'send'
      const r = await chatService.send(target, text.trim(), ids, channel)
      setSessionsVersion(v => v + 1)  // the title can change after the first description
      if (!live()) return true
      const reply = r.assistant_message ? toChat(r.assistant_message) : null
      setMessages(m => {
        const next = m.map(x => x.id === localId ? { ...toChat(r.user_message), attachments: x.attachments } : x)
        if (reply) next.push(reply)
        else next.push({ id: uid(), role: 'system', at: Date.now(), notice: r.ai_status === 'unavailable' ? 'ai_unavailable' : 'ai_error',
          text: r.ai_error?.message || 'The AI could not reply.', hint: r.ai_error?.hint, errorCode: r.ai_error?.code })
        return next
      })
      if (reply) setFreshReply(reply)
      sessionService.get(target).then(s => { if (live()) setSession(s) }).catch(() => undefined)  // picks up the server's title for a new chat
      return true
    } catch (e) {
      if (!live()) return false
      // Nothing reached the AI: take the unsent message back out so the composer can restore it.
      setMessages(m => m.filter(x => x.id !== localId))
      setDraft({ text, attachments })
      const msg = (e as ApiError).message || 'Something went wrong.'
      setError(stage === 'upload' ? `${msg} Your message was not sent; it is back in the box.` : stage === 'session' ? `Could not start the session: ${msg}` : `${msg} Your message is back in the box: try again.`)
      return false
    } finally { if (live()) { setThinking(false); setProgress(null); busy.current = false } }
  }, [])

  const newSession = useCallback(() => reset(), [reset])

  const setSessionTitle = useCallback((id: string, title: string) => {
    setSession(s => (s && s.id === id ? { ...s, title } : s)); setSessionsVersion(v => v + 1)
  }, [])

  // A different account signing in on this device must never see the previous account's open chat.
  // Only a change away from a signed-in account clears the chat (sign-out, or another account). The first sign-in check on
  // page load must not: the chat page has already started opening the conversation in the address bar, and clearing it then
  // threw the loaded messages away, so a refreshed or bookmarked chat stayed on its loading placeholder.
  const userId = useMaybeAuth()?.user?.id ?? null
  const lastUser = useRef<string | null>(null)
  useEffect(() => {
    if (lastUser.current && lastUser.current !== userId) reset()
    lastUser.current = userId
  }, [userId, reset])

  const value = useMemo<Ctx>(() => ({ collapsed, toggleCollapsed: () => setCollapsed(c => !c), sessionId, session, messages, thinking, progress, draft, clearDraft, error, openError,
    freshReply, sessionsVersion, refreshSessions, send, openSession, newSession, setSessionTitle }),
  [collapsed, sessionId, session, messages, thinking, progress, draft, clearDraft, error, openError, freshReply, sessionsVersion, refreshSessions, send, openSession, newSession, setSessionTitle])
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}

export function useApp() {
  const c = useContext(AppCtx)
  if (!c) throw new Error('useApp must be used inside AppProvider')
  return c
}
