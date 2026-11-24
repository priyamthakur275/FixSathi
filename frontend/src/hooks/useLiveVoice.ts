import { useCallback, useEffect, useRef, useState } from 'react'
import { tokens, refreshTokens, wsUrl } from '../services/api'
import type { Box, VoiceState } from '../types'

export interface LiveLine { id: number; role: 'user' | 'assistant'; text: string }
export interface LiveStep { id: string; step_number: number; title: string; instruction: string; requires_power_off: boolean }
export interface LivePart { url: string; found: boolean; component_name: string | null; explanation: string; box: Box | null }

const toB64 = (buf: ArrayBuffer) => { let s = ''; const b = new Uint8Array(buf); for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000)); return btoa(s) }
const fromB64 = (s: string) => Uint8Array.from(atob(s), c => c.charCodeAt(0))

/** Real Gemini Live voice through the FixSaathi backend relay. The browser never sees the API key. */
export function useLiveVoice(sessionId: string | null) {
  const [state, setState] = useState<VoiceState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [muted, setMuted] = useState(false)
  const [cameraOn, setCameraOn] = useState(false)
  const [lines, setLines] = useState<LiveLine[]>([])
  const [steps, setSteps] = useState<LiveStep[]>([])
  const [blocked, setBlocked] = useState<string | null>(null)
  const [diagnosis, setDiagnosis] = useState<string | null>(null)
  const [part, setPart] = useState<LivePart | null>(null)
  const [tool, setTool] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const micCtx = useRef<AudioContext | null>(null)
  const micStream = useRef<MediaStream | null>(null)
  const outCtx = useRef<AudioContext | null>(null)
  const playAt = useRef(0)
  const sources = useRef<AudioBufferSourceNode[]>([])
  const camStream = useRef<MediaStream | null>(null)
  const camTimer = useRef<number | null>(null)
  const videoEl = useRef<HTMLVideoElement | null>(null)
  const mutedRef = useRef(false)
  const lineId = useRef(0)

  const send = (m: object) => { if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(m)) }

  const stopPlayback = () => { sources.current.forEach(s => { try { s.stop() } catch { /* already stopped */ } }); sources.current = []; playAt.current = 0 }
  const play = (pcm: Uint8Array) => {
    const ctx = outCtx.current; if (!ctx) return
    const i16 = new Int16Array(pcm.buffer, pcm.byteOffset, Math.floor(pcm.byteLength / 2))
    const buf = ctx.createBuffer(1, i16.length, 24000); const ch = buf.getChannelData(0)
    for (let i = 0; i < i16.length; i++) ch[i] = i16[i] / 0x8000
    const src = ctx.createBufferSource(); src.buffer = buf; src.connect(ctx.destination)
    const t = Math.max(ctx.currentTime, playAt.current); src.start(t); playAt.current = t + buf.duration
    sources.current.push(src); src.onended = () => { sources.current = sources.current.filter(x => x !== src) }
  }
  const addLine = (role: 'user' | 'assistant', text: string) => setLines(ls => {
    const last = ls[ls.length - 1]
    if (last && last.role === role) return [...ls.slice(0, -1), { ...last, text: last.text + text }]
    return [...ls, { id: ++lineId.current, role, text }]
  })

  const stopCamera = useCallback(() => {
    if (camTimer.current) clearInterval(camTimer.current); camTimer.current = null
    camStream.current?.getTracks().forEach(t => t.stop()); camStream.current = null; setCameraOn(false)
  }, [])

  const cleanup = useCallback(() => {
    stopCamera()
    micStream.current?.getTracks().forEach(t => t.stop()); micStream.current = null
    void micCtx.current?.close(); micCtx.current = null
    stopPlayback(); void outCtx.current?.close(); outCtx.current = null
    if (ws.current && ws.current.readyState <= WebSocket.OPEN) ws.current.close(); ws.current = null
  }, [stopCamera])
  useEffect(() => cleanup, [cleanup])

  const stop = useCallback(() => { send({ type: 'end_session' }); cleanup(); setState('idle'); setTool(null) }, [cleanup])

  const start = useCallback(async (sid: string, language?: string) => {
    setError(null); setErrorCode(null); setBlocked(null); setState('connecting')
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser cannot use the microphone here. Use Chrome on localhost or HTTPS.')
      micStream.current = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
      micCtx.current = new AudioContext({ sampleRate: 16000 })
      await micCtx.current.audioWorklet.addModule('/mic-worklet.js')
      outCtx.current = new AudioContext({ sampleRate: 24000 })
      if (!tokens.access()) await refreshTokens()
    } catch (e) {
      cleanup(); setState('error')
      setError((e as DOMException).name === 'NotAllowedError' ? 'Microphone permission was denied. Allow it in the browser and try again.' : (e as Error).message); return
    }
    const sock = new WebSocket(wsUrl(`/api/v1/live/${sid}`)); ws.current = sock
    sock.onopen = () => sock.send(JSON.stringify({ type: 'auth', token: tokens.access(), language }))
    sock.onmessage = ev => {
      const m = JSON.parse(ev.data as string)
      switch (m.type) {
        case 'session_ready': {
          setState('listening')
          const ctx = micCtx.current!; const node = new AudioWorkletNode(ctx, 'mic-capture')
          node.port.onmessage = e => { if (!mutedRef.current) send({ type: 'audio_chunk', data: toB64(e.data as ArrayBuffer) }) }
          ctx.createMediaStreamSource(micStream.current!).connect(node); break
        }
        case 'audio_chunk': setState('responding'); play(fromB64(m.data)); break
        case 'transcription': addLine(m.role, m.text); break
        case 'assistant_text': addLine('assistant', m.text); break
        case 'interrupted': stopPlayback(); setState('listening'); break
        case 'turn_complete': setState('listening'); setTool(null); break
        case 'tool_call_status': setTool(m.status === 'running' ? m.name : null); if (m.status === 'running') setState('processing'); break
        case 'safety_blocked': setBlocked(m.step_title || 'A power-sensitive step'); break
        case 'safety_confirmation_required': setBlocked(b => b ?? 'Next step'); break
        case 'step': setSteps(s => [...s, m.step]); setBlocked(null); break
        case 'diagnosis': setDiagnosis(m.diagnosis.problem_summary); break
        case 'part_located': setPart({ url: m.url, found: m.found, component_name: m.component_name, explanation: m.explanation, box: m.box }); break
        case 'escalated': addLine('assistant', ' [Escalated to a senior technician]'); break
        case 'error': setErrorCode(m.code || null); if (m.fatal) { setError(m.message); setState('error'); cleanup() } else setError(m.message); break
        case 'session_ended': cleanup(); setState('idle'); break
      }
    }
    sock.onerror = () => { setError('Could not connect to the FixSaathi live server.'); setState('error') }
    sock.onclose = () => { setState(s => (s === 'error' ? s : 'idle')); cleanup() }
  }, [cleanup])

  const toggleMute = () => { mutedRef.current = !mutedRef.current; setMuted(mutedRef.current); if (mutedRef.current) send({ type: 'audio_stream_end' }) }

  const toggleCamera = useCallback(async (video: HTMLVideoElement | null) => {
    if (camStream.current) { stopCamera(); return }
    try {
      camStream.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } } })
      videoEl.current = video; if (video) { video.srcObject = camStream.current; await video.play().catch(() => undefined) }
      setCameraOn(true)
      const canvas = document.createElement('canvas')
      camTimer.current = window.setInterval(() => {
        const v = videoEl.current; if (!v || !v.videoWidth) return
        const w = Math.min(768, v.videoWidth); canvas.width = w; canvas.height = Math.round(v.videoHeight * w / v.videoWidth)
        canvas.getContext('2d')?.drawImage(v, 0, 0, canvas.width, canvas.height)
        const data = canvas.toDataURL('image/jpeg', 0.6).split(',')[1]
        if (data) send({ type: 'video_frame', data })
      }, 1000)
    } catch { setError('Camera permission was denied or no camera is available.') }
  }, [stopCamera])

  const sendText = (text: string) => { if (text.trim()) { addLine('user', text); send({ type: 'text_input', text }) } }

  return { state, error, errorCode, muted, cameraOn, lines, steps, blocked, diagnosis, part, tool, sessionId, start, stop, toggleMute, toggleCamera, sendText }
}
