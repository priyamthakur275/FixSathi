import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, tokens } from '../services/api'

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })

afterEach(() => { vi.restoreAllMocks(); tokens.clear() })

describe('api client', () => {
  it('parses the backend error envelope', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json(409, { error: { code: 'SAFETY_CONFIRMATION_REQUIRED', message: 'Record both', details: { missing: ['tester_checked'] } } })))
    const e = await api('/api/v1/x').catch(x => x) as ApiError
    expect(e).toBeInstanceOf(ApiError)
    expect(e.code).toBe('SAFETY_CONFIRMATION_REQUIRED')
    expect(e.details.missing).toEqual(['tester_checked'])
  })

  it('reports network failures without leaking details', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    const e = await api('/api/v1/x').catch(x => x) as ApiError
    expect(e.code).toBe('NETWORK')
    expect(e.message).toMatch(/^Cannot reach the FixSaathi server\./)
  })

  it('sends the bearer token and refreshes once on 401', async () => {
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    tokens.set('old-access', 'refresh-1')
    const seen: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      seen.push(`${url.replace(/^.*\/api/, '/api')} ${(init.headers as Record<string, string>)?.Authorization ?? ''}`)
      if (url.endsWith('/auth/refresh')) return json(200, { access_token: 'new-access', refresh_token: 'refresh-2' })
      return (init.headers as Record<string, string>).Authorization === 'Bearer new-access' ? json(200, { ok: true }) : json(401, { error: { code: 'TOKEN_EXPIRED', message: 'expired' } })
    }))
    expect(await api<{ ok: boolean }>('/api/v1/sessions')).toEqual({ ok: true })
    expect(seen).toEqual(['/api/v1/sessions Bearer old-access', '/api/v1/auth/refresh ', '/api/v1/sessions Bearer new-access'])
    expect(store['fixsaathi.refresh']).toBe('refresh-2')
  })

  it('times out slow requests', async () => {
    vi.stubGlobal('fetch', vi.fn((_u: string, init: RequestInit) => new Promise((_, rej) => init.signal?.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError'))))))
    const e = await api('/api/v1/x', { timeoutMs: 20 }).catch(x => x) as ApiError
    expect(e.code).toBe('TIMEOUT')
  })

  it('keeps the sign-in when the server is waking up (502 on refresh)', async () => {
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    tokens.set('old-access', 'refresh-1')
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/auth/refresh') ? new Response('Bad Gateway', { status: 502 }) : json(401, { error: { code: 'TOKEN_EXPIRED', message: 'expired' } })))
    const e = await api('/api/v1/sessions').catch(x => x) as ApiError
    expect(e.code).toBe('SERVER_WAKING')
    expect(store['fixsaathi.refresh']).toBe('refresh-1')
  })

  it('signs out only when the refresh token is really invalid', async () => {
    await new Promise(r => setTimeout(r, 5))  // let the previous test's shared refresh settle
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    tokens.set('old-access', 'refresh-1')
    vi.stubGlobal('fetch', vi.fn(async () => json(401, { error: { code: 'REFRESH_INVALID', message: 'no' } })))
    await api('/api/v1/sessions').catch(() => undefined)
    expect(store['fixsaathi.refresh']).toBeUndefined()
  })

  it('uses the token another tab just rotated instead of signing everyone out', async () => {
    await new Promise(r => setTimeout(r, 5))
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    tokens.set('old-access', 'refresh-1')
    const sent: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      if (!url.endsWith('/auth/refresh')) return init && (init.headers as Record<string, string>).Authorization === 'Bearer new-access' ? json(200, []) : json(401, { error: { code: 'TOKEN_EXPIRED', message: 'expired' } })
      const rt = JSON.parse(String(init?.body)).refresh_token as string
      sent.push(rt)
      if (rt === 'refresh-1') { store['fixsaathi.refresh'] = 'refresh-2'; return json(401, { error: { code: 'REFRESH_INVALID', message: 'used' } }) }  // the other tab won the race
      return json(200, { access_token: 'new-access', refresh_token: 'refresh-3' })
    }))
    await expect(api('/api/v1/sessions')).resolves.toEqual([])
    expect(sent).toEqual(['refresh-1', 'refresh-2'])
    expect(store['fixsaathi.refresh']).toBe('refresh-3')
  })

  it('turns proxy errors without a JSON body into a readable message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>503</html>', { status: 503, headers: { 'content-type': 'text/html' } })))
    const e = await api('/api/v1/x').catch(x => x) as ApiError
    expect(e.code).toBe('SERVER_WAKING')
    expect(e.message).toMatch(/starting up/)
  })
})
