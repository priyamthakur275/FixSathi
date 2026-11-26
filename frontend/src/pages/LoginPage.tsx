import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { Emblem, Wordmark } from '../components/common/Logo'
import { LockDemo } from '../components/repair/LockDemo'
import { useAuth } from '../context/AuthContext'
import type { ApiError } from '../services/api'


export default function LoginPage() {
  const { login, register } = useAuth()
  const nav = useNavigate(); const loc = useLocation()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [f, setF] = useState({ name: '', email: '', password: '', org: '' })
  const [busy, setBusy] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null)
    try {
      setShowPw(false)  // never leave a password visible after submitting
      if (mode === 'login') await login(f.email, f.password)
      else await register(f.name, f.email, f.password, f.org)
      nav((loc.state as { from?: string } | null)?.from || '/', { replace: true })
    } catch (x) {
      const a = x as ApiError
      setErr(a.code === 'VALIDATION_ERROR' ? 'Please check the form. Passwords need at least 8 characters.'
        : a.code === 'EMAIL_TAKEN' ? 'An account with this email already exists. Sign in instead.'
          : a.code === 'RATE_LIMITED' ? 'Too many attempts. Wait a minute and try again.'
            : a.status === 0 || a.code === 'NETWORK_ERROR' ? 'Cannot reach the server. Check your internet connection and try again.' : a.message)
    } finally { setBusy(false) }
  }
  const label = 'mb-1.5 block text-xs font-medium text-ink-2'
  return (
    <div className="grid min-h-dvh bg-bg lg:grid-cols-[1.05fr_1fr]">
      <aside className="fs-plate relative hidden overflow-hidden border-r border-line bg-bg-2 lg:flex lg:flex-col lg:justify-between lg:gap-10 lg:p-12 xl:p-14">
        <div className="relative flex items-center gap-3"><Emblem height={40} /><Wordmark height={19} /></div>
        <div className="relative max-w-[34rem]">
          <h2 className="font-display text-[36px] leading-[1.08] xl:text-[42px]">The repair copilot that won&apos;t let you open a live appliance.</h2>
          <p className="mt-5 max-w-md text-[15px] leading-relaxed text-ink-2">Diagnosis grounded in sourced repair records, voice in English, Hindi and Kannada, and power steps the server keeps locked until you have isolated the supply.</p>
          <div className="mt-8"><LockDemo /></div>
          {/* Figures from docs/EVALUATION.md (held-out v2 Hit@1; held-out safety set). 189 of the 377 records come from manufacturer
              documentation; the rest are labelled unverified, so they are "sourced", not "verified". */}
          <dl className="mt-8 grid grid-cols-3 gap-4">
            <div><dt className="text-xs text-ink-3">Right record ranked first</dt><dd className="num font-display mt-1 text-[22px]">94.4%</dd></div>
            <div><dt className="text-xs text-ink-3">Unsafe steps withheld</dt><dd className="num font-display mt-1 text-[22px]">12 of 12</dd></div>
            <div><dt className="text-xs text-ink-3">Sourced repair records</dt><dd className="num font-display mt-1 text-[22px]">377</dd></div>
          </dl>
        </div>
        <p className="relative text-xs text-ink-3">Built on Google Gemini by Team Tensor Trailblazers, BMS College of Engineering</p>
      </aside>

      <main className="flex items-center justify-center px-5 py-10">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="w-full max-w-[400px]">
          <div className="mb-8 flex flex-col items-center gap-3 lg:hidden"><Emblem height={64} /><Wordmark height={24} /><p className="text-sm text-ink-2">AI repair copilot for field technicians</p></div>
          <div className="card card-pad !p-7 shadow-[var(--shadow-lift)]">
            <form onSubmit={submit} className="space-y-4">
              <div>
                <h1 className="font-display text-[26px]">{mode === 'login' ? 'Sign in' : 'Create your account'}</h1>
                <p className="mt-1 text-sm text-ink-2">{mode === 'login' ? 'Welcome back. Pick up where you left off.' : 'Free to try. Your sessions and reports stay in your account.'}</p>
              </div>
              {mode === 'register' && <>
                <div><label className={label} htmlFor="name">Full name</label><input id="name" className="field" placeholder="e.g. Ravi Kumar" autoComplete="name" required minLength={2} value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></div>
                <div><label className={label} htmlFor="org">Organisation <span className="text-ink-3">(optional)</span></label><input id="org" className="field" placeholder="Service company" value={f.org} onChange={e => setF({ ...f, org: e.target.value })} /></div>
              </>}
              <div><label className={label} htmlFor="email">Email</label><input id="email" type="email" className="field" placeholder="you@company.com" autoComplete="email" required value={f.email} onChange={e => setF({ ...f, email: e.target.value })} /></div>
              <div>
                <label className={label} htmlFor="pw">Password</label>
                <div className="relative">
                  <input id="pw" type={showPw ? 'text' : 'password'} className="field !pr-12" placeholder={mode === 'register' ? 'At least 8 characters' : 'Your password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                    required minLength={mode === 'register' ? 8 : 1} maxLength={128} value={f.password} onChange={e => setF({ ...f, password: e.target.value })} aria-describedby={mode === 'register' ? 'pw-hint' : undefined} />
                  <button type="button" onClick={() => setShowPw(v => !v)} onMouseDown={e => e.preventDefault()} aria-label={showPw ? 'Hide password' : 'Show password'} aria-pressed={showPw} aria-controls="pw" title={showPw ? 'Hide password' : 'Show password'}
                    className="absolute right-1.5 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink">
                    {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {mode === 'register' && <p id="pw-hint" className={`mt-1.5 text-xs ${f.password.length === 0 ? 'text-ink-3' : f.password.length < 8 ? 'text-warn' : 'text-ok'}`}>{f.password.length === 0 ? 'Use at least 8 characters.' : f.password.length < 8 ? `${8 - f.password.length} more character${8 - f.password.length === 1 ? '' : 's'} needed.` : 'Looks good.'}</p>}
              </div>
              {err && <p role="alert" className="rounded-xl border border-crit/40 bg-crit/10 px-3 py-2 text-sm text-crit">{err}</p>}
              <button type="submit" disabled={busy} className="btn btn-primary w-full py-3 text-[15px]">{busy && <Loader2 size={16} className="animate-spin" />}{mode === 'login' ? 'Sign in' : 'Create account'}</button>
              <div className="flex items-center gap-3 text-[12px] text-ink-3"><span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" /></div>
              <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setErr(null); setShowPw(false) }} className="btn w-full">
                {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in'}
              </button>
            </form>
          </div>
          <p className="mt-6 text-center text-xs text-ink-3">AI suggestions are estimates. Always verify isolation with your own tester.</p>
        </motion.div>
      </main>
    </div>
  )
}
