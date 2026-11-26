/** Central HTTP client. Base URL from VITE_API_BASE_URL. No secrets ever live in the frontend. */
const RAW = import.meta.env.VITE_API_BASE_URL as string | undefined
// Unset: local dev default. Empty string: same origin (production single-service deploy).
const BASE = RAW === undefined ? 'http://localhost:8000' : RAW.replace(/\/$/, '')
const REFRESH_KEY = 'fixsaathi.refresh'

export class ApiError extends Error {
  status: number; code: string; details: Record<string, unknown>
  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) { super(message); this.status = status; this.code = code; this.details = details }
}

let accessToken: string | null = null
let onSignedOut: (() => void) | null = null
let refreshing: Promise<RefreshResult> | null = null
/** ok: new tokens; invalid: the sign-in is really over; transient: server waking up or offline, keep the sign-in. */
type RefreshResult = 'ok' | 'invalid' | 'transient'

export const tokens = {
  set(access: string, refresh: string) { accessToken = access; try { localStorage.setItem(REFRESH_KEY, refresh) } catch { /* storage unavailable */ } },
  clear() { accessToken = null; try { localStorage.removeItem(REFRESH_KEY) } catch { /* ignore */ } },
  refresh(): string | null { try { return localStorage.getItem(REFRESH_KEY) } catch { return null } },
  access: () => accessToken,
  onSignedOut(fn: () => void) { onSignedOut = fn },
}

export const apiBase = BASE
export const wsUrl = (path: string) => (BASE || window.location.origin).replace(/^http/, 'ws') + path

async function parse(res: Response): Promise<unknown> {
  if (res.status === 204) return null
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res.text()
}

function toError(status: number, body: unknown): ApiError {
  const e = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } })?.error
  if (e) return new ApiError(status, e.code || 'ERROR', e.message || 'Request failed', e.details || {})
  if ([502, 503, 504].includes(status)) return new ApiError(status, 'SERVER_WAKING', 'The server is starting up or busy. Wait a few seconds and try again.')
  if (status === 413) return new ApiError(status, 'UPLOAD_TOO_LARGE', 'That file is too large to upload.')
  return new ApiError(status, status === 0 ? 'NETWORK' : 'ERROR', status === 0 ? 'Cannot reach the FixSaathi server. Check your internet connection.' : `Request failed (${status}).`)
}

export async function refreshTokens(): Promise<boolean> { return (await refreshDetailed()) === 'ok' }

export async function refreshDetailed(): Promise<RefreshResult> {
  const rt = tokens.refresh()
  if (!rt) return 'invalid'
  const attempt = async (sent: string, again: boolean): Promise<RefreshResult> => {
    const r = await fetch(`${BASE}/api/v1/auth/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: sent }) })
    if (r.status === 401 || r.status === 422) {
      // Refresh tokens rotate. If another tab refreshed while this request was in flight, localStorage already holds the
      // new token: use it rather than clearing it, which would sign every tab out.
      const latest = tokens.refresh()
      if (!again && latest && latest !== sent) return attempt(latest, true)
      if (tokens.refresh() === sent) tokens.clear()
      return 'invalid'
    }
    if (!r.ok) return 'transient'  // e.g. 502/503 while the server wakes up: do NOT sign the user out
    const d = await r.json() as { access_token: string; refresh_token: string }
    tokens.set(d.access_token, d.refresh_token); return 'ok'
  }
  refreshing ??= (async (): Promise<RefreshResult> => {
    try { return await attempt(rt, false) } catch { return 'transient' } finally { setTimeout(() => { refreshing = null }, 0) }
  })()
  return refreshing
}

interface Opts { method?: string; body?: unknown; form?: FormData; timeoutMs?: number; signal?: AbortSignal; raw?: boolean }

export async function api<T>(path: string, o: Opts = {}, retried = false): Promise<T> {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort('timeout'), o.timeoutMs ?? 30000)
  o.signal?.addEventListener('abort', () => ctl.abort('cancelled'))
  const headers: Record<string, string> = {}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  if (o.body !== undefined) headers['Content-Type'] = 'application/json'
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { method: o.method || (o.body !== undefined || o.form ? 'POST' : 'GET'), headers, body: o.form ?? (o.body !== undefined ? JSON.stringify(o.body) : undefined), signal: ctl.signal })
  } catch {
    clearTimeout(timer)
    if (ctl.signal.aborted && ctl.signal.reason === 'timeout') throw new ApiError(0, 'TIMEOUT', 'The server took too long to respond.')
    if (ctl.signal.aborted) throw new ApiError(0, 'CANCELLED', 'Request cancelled.')
    throw toError(0, null)
  }
  clearTimeout(timer)
  if (res.status === 401 && !retried && !path.startsWith('/api/v1/auth/')) {
    const r = await refreshDetailed()
    if (r === 'ok') return api<T>(path, o, true)
    if (r === 'transient') throw new ApiError(503, 'SERVER_WAKING', 'The server is starting up. Wait a few seconds and try again.')
    tokens.clear(); onSignedOut?.()
  }
  if (o.raw && res.ok) return res as unknown as T
  const body = await parse(res)
  if (!res.ok) throw toError(res.status, body)
  return body as T
}

/** Fetch a protected image and return an object URL for <img src>. */
export async function mediaUrl(path: string): Promise<string> {
  const r = await api<Response>(path, { raw: true })
  return URL.createObjectURL(await r.blob())
}
