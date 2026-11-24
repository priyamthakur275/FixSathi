import { useCallback, useEffect, useRef, useState } from 'react'
import { speech, SPEECH_LANG } from '../services/speech'

/* eslint-disable @typescript-eslint/no-explicit-any */
const getRec = (): any => (typeof window !== 'undefined' ? ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) : null)

export type DictationState = 'idle' | 'starting' | 'listening' | 'finishing'

/**
 * Push-to-talk dictation. The technician starts it, speaks for as long as needed, and presses Done: only then is the text final.
 * Nothing is sent while they pause, because recognition restarts by itself after silence until Done or Cancel is pressed.
 * The waveform uses the real microphone level (an AnalyserNode), not an animation.
 */
export function useDictation(language: string) {
  const [state, setState] = useState<DictationState>('idle')
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const rec = useRef<any>(null)
  const want = useRef(false)          // true from Start until Done/Cancel
  const committed = useRef('')        // final text from earlier recognition runs (each restart starts its result list again)
  const current = useRef({ final: '', interim: '' })
  const finish = useRef<((t: string) => void) | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const ctx = useRef<AudioContext | null>(null)
  const analyser = useRef<AnalyserNode | null>(null)
  const restart = useRef<() => void>(() => undefined)
  const supported = !!getRec()

  const joined = () => [committed.current, current.current.final, current.current.interim].map(s => s.trim()).filter(Boolean).join(' ')

  const release = useCallback(() => {
    stream.current?.getTracks().forEach(t => t.stop()); stream.current = null
    void ctx.current?.close().catch(() => undefined); ctx.current = null; analyser.current = null
  }, [])

  const begin = useCallback(() => {
    const Rec = getRec(); const r = new Rec(); rec.current = r
    r.lang = SPEECH_LANG[language] || 'en-IN'; r.continuous = true; r.interimResults = true; r.maxAlternatives = 1
    current.current = { final: '', interim: '' }
    r.onresult = (ev: any) => {
      let final = '', interim = ''
      for (let i = 0; i < ev.results.length; i++) {
        const t = String(ev.results[i][0]?.transcript ?? '')
        if (ev.results[i].isFinal) final += t; else interim += t
      }
      current.current = { final, interim }; setText(joined())
    }
    r.onerror = (e: any) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') { want.current = false; setError('mic-denied') }
      else if (e.error === 'network') { want.current = false; setError('network') }
      else if (e.error === 'audio-capture') { want.current = false; setError('no-mic') }
      // 'no-speech' and 'aborted' are normal during pauses: onend restarts or finishes.
    }
    r.onend = () => {
      // Keep everything this run heard, including a phrase still marked interim: the browser can end a run in a pause before
      // finalising it, and those words would otherwise be lost.
      committed.current = [committed.current, current.current.final, current.current.interim].map(s => s.trim()).filter(Boolean).join(' ')
      current.current = { final: '', interim: '' }
      if (finish.current) { const done = finish.current; finish.current = null; rec.current = null; release(); setState('idle'); done(committed.current); return }
      if (want.current) { try { restart.current() } catch { /* restarted too fast; the next onend retries */ } return }
      rec.current = null; release(); setState('idle')
    }
    r.start()
  }, [language, release])
  useEffect(() => { restart.current = begin }, [begin])

  const start = useCallback(async () => {
    if (!getRec()) { setError('unsupported'); return }
    if (want.current) return  // one microphone session at a time
    speech.stop()             // never listen while FixSaathi is still talking
    setError(null); setText(''); committed.current = ''; finish.current = null; want.current = true; setState('starting')
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      const AC = window.AudioContext || (window as any).webkitAudioContext
      ctx.current = new AC(); const a = ctx.current!.createAnalyser(); a.fftSize = 256; a.smoothingTimeConstant = 0.6
      ctx.current!.createMediaStreamSource(stream.current).connect(a); analyser.current = a
    } catch (e) {
      want.current = false; release(); setState('idle')
      setError((e as DOMException)?.name === 'NotAllowedError' ? 'mic-denied' : 'no-mic'); return
    }
    if (!want.current) { release(); return }  // cancelled while the permission prompt was open
    try { begin(); setState('listening') } catch { want.current = false; release(); setState('idle'); setError('no-mic') }
  }, [begin, release])

  /** Stops the microphone and resolves with the complete text, after the recogniser delivers its last result. */
  const done = useCallback(() => new Promise<string>(resolve => {
    want.current = false
    if (!rec.current) { release(); setState('idle'); resolve(joined()); return }
    setState('finishing')
    const timer = setTimeout(() => { if (finish.current) { finish.current = null; try { rec.current?.abort() } catch { /* ignore */ } rec.current = null; release(); setState('idle'); resolve(joined()) } }, 2500)
    finish.current = t => { clearTimeout(timer); resolve(t) }
    try { rec.current.stop() } catch { finish.current = null; clearTimeout(timer); release(); setState('idle'); resolve(joined()) }
  }), [release])

  const cancel = useCallback(() => {
    want.current = false; finish.current = null
    try { rec.current?.abort() } catch { /* ignore */ }
    rec.current = null; release(); setState('idle'); setText(''); committed.current = ''
  }, [release])

  useEffect(() => () => { want.current = false; finish.current = null; try { rec.current?.abort() } catch { /* ignore */ } release() }, [release])

  /** 0..1 microphone loudness right now, for the waveform. */
  const level = useCallback(() => {
    const a = analyser.current; if (!a) return 0
    const buf = new Uint8Array(a.fftSize); a.getByteTimeDomainData(buf)
    let sum = 0; for (const v of buf) { const x = (v - 128) / 128; sum += x * x }
    return Math.min(1, Math.sqrt(sum / buf.length) * 4)
  }, [])

  return { supported, state, active: state !== 'idle', text, error, start, done, cancel, level, clearError: () => setError(null) }
}
