import { useCallback, useEffect, useRef, useState } from 'react'
import { chatService, repairService } from '../services'
import { speakable } from '../utils/text'
import type { Diagnosis, VoiceState } from '../types'
import type { LiveLine, LiveStep, LivePart } from './useLiveVoice'

/* eslint-disable @typescript-eslint/no-explicit-any */
const Rec: any = typeof window !== 'undefined' ? ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) : null
const LANG: Record<string, string> = { English: 'en-IN', Hindi: 'hi-IN', Kannada: 'kn-IN', Tamil: 'ta-IN' }

/** Fallback voice mode: the browser's speech recognition and speech synthesis around the normal, safety-gated text chat.
 *  Used when the Gemini Live model is not available to the server's API key. Same server-side safety rules apply. */
export function useBrowserVoice() {
  const [state, setState] = useState<VoiceState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [muted, setMuted] = useState(false)
  const [lines, setLines] = useState<LiveLine[]>([])
  const [diag, setDiag] = useState<Diagnosis | null>(null)
  const [steps, setSteps] = useState<LiveStep[]>([])
  const [blocked, setBlocked] = useState<string | null>(null)
  const [analysing, setAnalysing] = useState(false)
  const busy = useRef(false)
  const turns = useRef(0)
  const analysedAt = useRef(0)
  const rec = useRef<any>(null)
  const active = useRef(false)
  const mutedRef = useRef(false)
  const sidRef = useRef<string | null>(null)
  const langRef = useRef('en-IN')
  const id = useRef(0)
  const supported = !!Rec

  const add = (role: 'user' | 'assistant', text: string) => setLines(ls => [...ls, { id: ++id.current, role, text }])

  /** After each answer, run the server's diagnosis and step generation (the same safety-gated services the text chat uses). */
  const analyse = async () => {
    const sid = sidRef.current; if (!sid || busy.current) return
    busy.current = true; setAnalysing(true)
    try {
      setDiag(await repairService.diagnose(sid))
      const st = await repairService.generateSteps(sid)
      setSteps(st.map(x => ({ id: x.id, step_number: x.step_number, title: x.title, instruction: x.instruction || 'Locked until the safety checks are recorded.', requires_power_off: x.requires_power_off })))
      const locked = st.find(x => x.locked)
      setBlocked(locked ? locked.title : null)
    } catch (e) { setError(`Analysis: ${(e as Error).message || 'could not run'}`) }
    finally { busy.current = false; setAnalysing(false) }
  }

  // Each analysis costs 2 Gemini calls, so it runs once the technician has given enough detail (2 turns), not on every sentence.
  const maybeAnalyse = () => { if (turns.current >= 2 && analysedAt.current === 0) { analysedAt.current = turns.current; void analyse() } }

  const listenRef = useRef<() => void>(() => undefined)
  const listen = useCallback(() => {
    if (!active.current || mutedRef.current || !Rec) return
    const r = new Rec(); rec.current = r
    r.lang = langRef.current; r.interimResults = false; r.continuous = false; r.maxAlternatives = 1
    r.onresult = async (ev: any) => {
      const text = String(ev.results?.[0]?.[0]?.transcript || '').trim()
      if (!text || !sidRef.current) return
      add('user', text); turns.current++; setState('processing'); setError(null)
      try {
        const res = await chatService.send(sidRef.current, text, [], 'voice')
        const reply = res.assistant_message?.message || ''
        if (!reply) { setError([res.ai_error?.message || 'The AI could not reply.', res.ai_error?.code === 'QUOTA_EXCEEDED' ? 'Say it again in a few seconds.' : ''].join(' ').trim()); setState('listening'); listenRef.current(); return }
        add('assistant', reply); setState('responding'); maybeAnalyse()
        const u = new SpeechSynthesisUtterance(speakable(reply)); u.lang = langRef.current
        u.onend = () => { if (active.current) { setState('listening'); listenRef.current() } }
        u.onerror = u.onend
        window.speechSynthesis.cancel(); window.speechSynthesis.speak(u)
      } catch (e) { setError((e as Error).message || 'Request failed.'); setState('listening'); listenRef.current() }
    }
    r.onerror = (e: any) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') { setError('Microphone permission was denied. Allow it in the browser and try again.'); active.current = false; setState('error') }
      else if (e.error === 'no-speech' || e.error === 'aborted') { /* restart in onend */ }
      else setError(`Speech recognition: ${e.error}`)
    }
    r.onend = () => { if (active.current && !mutedRef.current && window.speechSynthesis && !window.speechSynthesis.speaking) setState(s => { if (s === 'listening') setTimeout(() => listenRef.current(), 250); return s }) }
    try { r.start(); setState('listening') } catch { /* already started */ }
  }, [])
  useEffect(() => { listenRef.current = listen }, [listen])

  const start = useCallback(async (sid: string, language?: string) => {
    setError(null)
    if (!Rec) { setState('error'); setError('This browser has no speech recognition. Use Chrome.'); return }
    sidRef.current = sid; langRef.current = LANG[language || 'English'] || 'en-IN'
    active.current = true; setState('connecting')
    try { const s = await navigator.mediaDevices.getUserMedia({ audio: true }); s.getTracks().forEach(t => t.stop()) }
    catch { active.current = false; setState('error'); setError('Microphone permission was denied. Allow it in the browser and try again.'); return }
    listen()
  }, [listen])

  const stop = useCallback(() => {
    active.current = false
    try { rec.current?.abort() } catch { /* ignore */ }
    window.speechSynthesis?.cancel(); setState('idle')
  }, [])

  const toggleMute = () => {
    mutedRef.current = !mutedRef.current; setMuted(mutedRef.current)
    if (mutedRef.current) { try { rec.current?.abort() } catch { /* ignore */ } } else listen()
  }
  const sendText = async (text: string) => {
    if (!text.trim() || !sidRef.current) return
    add('user', text); turns.current++; setState('processing'); setError(null)
    try {
      const res = await chatService.send(sidRef.current, text, [])
      const reply = res.assistant_message?.message || ''
      if (reply) { add('assistant', reply); maybeAnalyse() } else setError(res.ai_error?.message || 'The AI could not reply.')
    } catch (e) { setError((e as Error).message) }
    setState('listening')
  }
  useEffect(() => () => { active.current = false; try { rec.current?.abort() } catch { /* ignore */ } window.speechSynthesis?.cancel() }, [])

  const none = null as null
  return { supported, state, error, muted, cameraOn: false, lines, steps, blocked, diagnosis: (diag?.problem_summary ?? null) as string | null, diag, analysing,
    part: none as LivePart | null, tool: none as string | null, start, stop, toggleMute, analyse: () => { analysedAt.current = turns.current; void analyse() }, toggleCamera: async (_v: HTMLVideoElement | null) => undefined, sendText }
}
