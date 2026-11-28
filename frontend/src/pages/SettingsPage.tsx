import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, Loader2, LogOut, Monitor, Moon, Play, Sun, SunMedium } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useApp } from '../context/AppContext'
import { usePrefs, type Rate, type Theme } from '../context/PrefsContext'
import { AI_VOICES, onVoicesChanged, speech, speechSupported, testPersonalVoice, voicesFor, type PersonalTest } from '../services/speech'
import { LANG_NATIVE, useT, type Key } from '../i18n'
import type { Language } from '../types'

const LANGS: Language[] = ['English', 'Hindi', 'Kannada']

function Section({ title, hint, children, right }: { title: string; hint?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="border-b border-line py-6 last:border-0">
      <div className="mb-3 flex items-center justify-between gap-3"><h2 className="font-semibold">{title}</h2>{right}</div>
      {hint && <p className="-mt-1.5 mb-3.5 text-sm text-ink-2">{hint}</p>}
      {children}
    </section>
  )
}

function Segmented<T extends string | number>({ value, options, onChange, label }: { value: T; options: { v: T; label: string; icon?: ReactNode }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap gap-1 rounded-xl border border-line bg-surface p-1">
      {options.map(o => (
        <button key={String(o.v)} role="radio" aria-checked={value === o.v} onClick={() => onChange(o.v)}
          className={`inline-flex min-h-[44px] items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${value === o.v ? 'bg-surface-3 text-ink shadow-sm' : 'text-ink-2 hover:text-ink'}`}>{o.icon}{o.label}</button>
      ))}
    </div>
  )
}

export default function SettingsPage() {
  const t = useT()
  const { user, setLanguage, logout } = useAuth()
  const { newSession } = useApp()
  const prefs = usePrefs()
  const nav = useNavigate()
  const [busy, setBusy] = useState<Language | null>(null)
  const [saved, setSaved] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const language = user?.preferred_language ?? 'English'
  const [voices, setVoices] = useState(() => voicesFor(language))
  useEffect(() => { setVoices(voicesFor(language)); return onVoicesChanged(() => setVoices(voicesFor(language))) }, [language])
  useEffect(() => () => speech.stop(), [])

  const pick = async (l: Language) => {
    if (l === language) return
    setBusy(l); setErr(null); setSaved(false)
    try { await setLanguage(l); setSaved(true); setTimeout(() => setSaved(false), 2000) } catch (e) { setErr((e as Error).message) } finally { setBusy(null) }
  }
  const [pTest, setPTest] = useState<PersonalTest | 'busy' | null>(null)
  const testPersonal = async () => { setPTest('busy'); setPTest(await testPersonalVoice()) }
  const test = () => speech.speak(t('settings.voiceSample'), { language, voiceURI: prefs.voiceURI, rate: prefs.rate, aiVoice: 'device' })
  const signOut = async () => { speech.stop(); await logout(); newSession(); nav('/login', { replace: true }) }

  return (
    <div className="page page-read">
      <h1 className="font-display text-[26px] leading-tight md:text-[34px]">{t('settings.title')}</h1>

      <div className="mt-4">
        <Section title={t('settings.language')} hint={t('settings.languageHint')} right={busy ? <Loader2 size={15} className="animate-spin text-ink-3" /> : saved ? <span className="inline-flex items-center gap-1 text-xs text-accent"><Check size={13} />{t('settings.saved')}</span> : null}>
          <div role="radiogroup" aria-label={t('settings.language')} className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {LANGS.map(l => (
              <button key={l} role="radio" aria-checked={language === l} disabled={!!busy} onClick={() => void pick(l)}
                className={`flex min-h-[52px] flex-col items-start justify-center rounded-xl border px-3.5 py-2.5 text-left transition-colors ${language === l ? 'border-accent bg-accent/10' : 'border-line bg-surface hover:border-line-2'}`}>
                <span className="text-sm font-semibold">{LANG_NATIVE[l]}</span><span className="text-xs text-ink-3">{l}</span>
              </button>
            ))}
          </div>
          <label className="mt-3 flex min-h-[48px] cursor-pointer items-center justify-between gap-4 rounded-xl border border-line bg-surface px-4 py-3">
            <div>
              <span className="block text-sm font-medium">{t('settings.hindiFirst')}</span>
              <span className="block text-xs text-ink-3">{t('settings.hindiFirstHint')}</span>
            </div>
            <input type="checkbox" role="switch" checked={prefs.hindiFirst} onChange={e => prefs.setHindiFirst(e.target.checked)} className="peer sr-only" />
            <span aria-hidden className="relative h-6 w-11 shrink-0 rounded-full bg-surface-3 transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:bg-accent peer-checked:after:translate-x-5 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-accent" />
          </label>
          {err && <p role="alert" className="mt-2 text-sm text-crit">{err}</p>}
        </Section>

        <Section title={t('settings.appearance')} hint={t('settings.sunlightHint')}>
          <Segmented<Theme> label={t('settings.appearance')} value={prefs.theme} onChange={prefs.setTheme} options={[
            { v: 'dark', label: t('settings.dark'), icon: <Moon size={15} /> },
            { v: 'light', label: t('settings.light'), icon: <Sun size={15} /> },
            { v: 'sunlight', label: t('settings.sunlight'), icon: <SunMedium size={15} /> },
            { v: 'system', label: t('settings.system'), icon: <Monitor size={15} /> }]} />
        </Section>

        <Section title={t('settings.voice')} hint={t('settings.voiceHint')}>
          <label className="mb-4 flex min-h-[48px] cursor-pointer items-center justify-between gap-4 rounded-xl border border-line bg-surface px-4 py-3">
            <span className="text-sm font-medium">{t('settings.speakReplies')}</span>
            <input type="checkbox" role="switch" checked={prefs.speaker} onChange={e => { if (!e.target.checked) speech.stop(); prefs.setSpeaker(e.target.checked) }} className="peer sr-only" />
            <span aria-hidden className="relative h-6 w-11 shrink-0 rounded-full bg-surface-3 transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:bg-accent peer-checked:after:translate-x-5 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-accent" />
          </label>
          <div className="mb-4">
            <label htmlFor="ai-voice" className="mb-1 block text-sm font-medium">{t('settings.aiVoice')}</label>
            <p className="mb-2 text-xs text-ink-3">{t('settings.aiVoiceHint')}</p>
            <select id="ai-voice" value={prefs.aiVoice} onChange={e => prefs.setAiVoice(e.target.value)} className="field w-full !py-2.5 text-sm">
              {AI_VOICES.map(v => <option key={v} value={v}>{t(`voice.v.${v}` as Key)}</option>)}
              <option value="device">{t('settings.deviceOnly')}</option>
            </select>
            <details className="mt-2.5 rounded-xl border border-line bg-surface/50 px-3.5 py-2.5">
              <summary className="cursor-pointer text-xs font-medium text-ink-2">{t('settings.voiceDiagnostics')}</summary>
              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <button onClick={() => void testPersonal()} disabled={pTest === 'busy'} className="btn btn-sm">{pTest === 'busy' ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}{t('settings.testPersonal')}</button>
                {pTest && pTest !== 'busy' && (pTest.ok
                  ? <span role="status" className="text-xs text-accent">{t('settings.testPersonalOk')} · {pTest.model} · {pTest.voiceId}</span>
                  : <span role="alert" className="text-xs text-crit">{t('settings.testPersonalFail')} {pTest.code}: {pTest.message}</span>)}
              </div>
            </details>
          </div>
          {!speechSupported() || voices.length === 0 ? <p className="text-sm text-ink-2">{t('settings.noVoices')}</p> : (
            <div className="space-y-4">
              <label className="-mb-2 block text-sm font-medium" htmlFor="voice">{t('settings.deviceVoice')}</label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <select id="voice" value={prefs.voiceURI && voices.some(v => v.voiceURI === prefs.voiceURI) ? prefs.voiceURI : ''} onChange={e => prefs.setVoice(e.target.value || null)} className="field flex-1 !py-2.5 text-sm">
                  <option value="">{t('settings.voiceAuto')}{voices[0] ? ` · ${voices[0].name}` : ''}</option>
                  {voices.map(v => <option key={v.voiceURI} value={v.voiceURI}>{v.name} ({v.lang})</option>)}
                </select>
                <button onClick={test} className="btn"><Play size={14} />{t('settings.testDevice')}</button>
              </div>
              <div>
                <p className="mb-2 text-sm text-ink-2">{t('settings.speed')}</p>
                <Segmented<Rate> label={t('settings.speed')} value={prefs.rate} onChange={prefs.setRate} options={[
                  { v: 0.92, label: t('settings.relaxed') }, { v: 1, label: t('settings.natural') }, { v: 1.1, label: t('settings.brisk') }]} />
              </div>
            </div>
          )}
        </Section>

        {user && (
          <Section title={t('settings.account')}>
            <div className="flex items-center gap-4 rounded-xl border border-line bg-surface p-4">
              <span className="fs-accent-bg flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-base font-semibold text-white" aria-hidden>{(user.full_name.trim()[0] || '?').toUpperCase()}</span>
              <div className="min-w-0 flex-1 leading-snug">
                <p className="truncate font-medium">{user.full_name}</p>
                <p className="truncate text-sm text-ink-2">{user.email}</p>
                <p className="text-xs text-ink-3">{t(`role.${user.role}` as Key)}{user.organisation_name ? ` · ${user.organisation_name}` : ''}</p>
              </div>
              <button onClick={() => void signOut()} className="btn btn-sm"><LogOut size={14} />{t('nav.signOut')}</button>
            </div>
          </Section>
        )}
      </div>
    </div>
  )
}
