import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { AI_VOICES, speech } from '../services/speech'

/** Device preferences: theme, speaker, voice and Hindi-first greeting. They belong to the device (voices differ per device),
 *  so they are kept in localStorage. Account settings such as language are saved on the server instead (see AuthContext). */
export type Theme = 'dark' | 'light' | 'sunlight' | 'system'
export type ResolvedTheme = 'dark' | 'light' | 'sunlight'
export type Rate = 0.92 | 1 | 1.1

/** aiVoice: a Gemini voice name (natural voice), or 'device' to always use the browser's voice. */
interface Prefs { theme: Theme; speaker: boolean; voiceURI: string | null; rate: Rate; aiVoice: string; hindiFirst: boolean }
interface Ctx extends Prefs {
  resolvedTheme: ResolvedTheme
  setTheme: (t: Theme) => void
  setSpeaker: (on: boolean) => void
  setVoice: (uri: string | null) => void
  setRate: (r: Rate) => void
  setAiVoice: (v: string) => void
  setHindiFirst: (on: boolean) => void
}

const KEYS = { theme: 'fixsaathi.theme', speaker: 'fixsaathi.speaker', voice: 'fixsaathi.voice', rate: 'fixsaathi.rate', aiVoice: 'fixsaathi.aiVoice', hindiFirst: 'fixsaathi.hindiFirst' }
const read = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const write = (k: string, v: string | null) => { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v) } catch { /* storage unavailable */ } }
const systemLight = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-color-scheme: light)').matches

const PrefsCtx = createContext<Ctx | null>(null)

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => (['dark', 'light', 'sunlight', 'system'].includes(read(KEYS.theme) ?? '') ? read(KEYS.theme) as Theme : 'system'))
  const [speaker, setSpeakerState] = useState(() => read(KEYS.speaker) !== 'off')
  const [voiceURI, setVoiceState] = useState<string | null>(() => read(KEYS.voice))
  const [rate, setRateState] = useState<Rate>(() => ({ '0.92': 0.92, '1.1': 1.1 } as Record<string, Rate>)[read(KEYS.rate) ?? ''] ?? 1)
  const [aiVoice, setAiVoiceState] = useState<string>(() => { const v = read(KEYS.aiVoice); return v && (v === 'device' || (AI_VOICES as readonly string[]).includes(v)) ? v : 'personal' })
  const [hindiFirst, setHindiFirstState] = useState(() => read(KEYS.hindiFirst) === 'on')
  const [sysLight, setSysLight] = useState(systemLight)

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: light)')
    if (!mq) return
    const on = () => setSysLight(mq.matches)
    mq.addEventListener?.('change', on)
    return () => mq.removeEventListener?.('change', on)
  }, [])

  const resolvedTheme: ResolvedTheme = theme === 'system' ? (sysLight ? 'light' : 'dark') : theme
  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme
    const metaColor = resolvedTheme === 'sunlight' ? '#ffffff' : resolvedTheme === 'light' ? '#f2f4f7' : '#090c11'
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', metaColor)
  }, [resolvedTheme])

  const setTheme = useCallback((t: Theme) => { setThemeState(t); write(KEYS.theme, t) }, [])
  // Speaker off silences FixSaathi at once, wherever it is switched (composer, settings).
  const setSpeaker = useCallback((on: boolean) => { if (!on) speech.stop(); setSpeakerState(on); write(KEYS.speaker, on ? 'on' : 'off') }, [])
  const setAiVoice = useCallback((v: string) => { setAiVoiceState(v); write(KEYS.aiVoice, v) }, [])
  const setVoice = useCallback((uri: string | null) => { setVoiceState(uri); write(KEYS.voice, uri) }, [])
  const setRate = useCallback((r: Rate) => { setRateState(r); write(KEYS.rate, String(r)) }, [])
  const setHindiFirst = useCallback((on: boolean) => { setHindiFirstState(on); write(KEYS.hindiFirst, on ? 'on' : 'off') }, [])

  const value = useMemo(() => ({ theme, speaker, voiceURI, rate, aiVoice, hindiFirst, resolvedTheme, setTheme, setSpeaker, setVoice, setRate, setAiVoice, setHindiFirst }),
    [theme, speaker, voiceURI, rate, aiVoice, hindiFirst, resolvedTheme, setTheme, setSpeaker, setVoice, setRate, setAiVoice, setHindiFirst])
  return <PrefsCtx.Provider value={value}>{children}</PrefsCtx.Provider>
}

export function usePrefs() {
  const c = useContext(PrefsCtx)
  if (!c) throw new Error('usePrefs must be used inside PrefsProvider')
  return c
}
