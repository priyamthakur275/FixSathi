import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError, refreshDetailed, tokens } from '../services/api'
import { authService } from '../services'
import type { Language, User } from '../types'

interface Ctx {
  user: User | null
  loading: boolean
  /** True while the first check is waiting for a sleeping server to wake up. */
  waking: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string, org?: string) => Promise<void>
  logout: () => Promise<void>
  setLanguage: (l: Language) => Promise<void>
}
const AuthCtx = createContext<Ctx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [waking, setWaking] = useState(false)
  useEffect(() => {
    tokens.onSignedOut(() => setUser(null))
    let live = true
    ;(async () => {
      // A free-tier server can take up to a minute to wake. Keep the saved sign-in and retry instead of signing out.
      const waits = [0, 2000, 3000, 5000, 8000, 12000, 15000]
      try {
        for (const w of waits) {
          if (!live) return
          if (w) { setWaking(true); await new Promise(r => setTimeout(r, w)) }
          const r = await refreshDetailed()
          if (r === 'invalid') return
          if (r === 'transient') continue
          try { const u = await authService.currentUser(); if (live) setUser(u); return }
          catch (e) { const a = e as ApiError; if (a.status === 401) { tokens.clear(); return } if (a.status && a.status < 500) return }
        }
      } finally { if (live) { setLoading(false); setWaking(false) } }
    })()
    return () => { live = false }
  }, [])
  const login = useCallback(async (e: string, p: string) => { setUser(await authService.login(e, p)) }, [])
  const register = useCallback(async (n: string, e: string, p: string, o?: string) => { setUser(await authService.register(n, e, p, o)) }, [])
  const logout = useCallback(async () => { await authService.logout(); setUser(null) }, [])
  const setLanguage = useCallback(async (l: Language) => { setUser(await authService.updateMe({ preferred_language: l })) }, [])
  const value = useMemo(() => ({ user, loading, waking, login, register, logout, setLanguage }), [user, loading, waking, login, register, logout, setLanguage])
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

/** The auth context when inside AuthProvider, otherwise null (for components that also render on their own, e.g. in tests). */
export function useMaybeAuth() { return useContext(AuthCtx) }

export function useAuth() {
  const c = useContext(AuthCtx)
  if (!c) throw new Error('useAuth must be used inside AuthProvider')
  return c
}
