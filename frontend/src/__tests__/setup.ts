// Shared browser stubs for component tests (jsdom has no media, object URLs or layout).
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

function ensureLocalStorage() {
  if (typeof globalThis.localStorage !== 'undefined') return
  const mem: Record<string, string> = {}
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: {
      getItem: (k: string) => (k in mem ? mem[k] : null),
      setItem: (k: string, v: string) => { mem[k] = String(v) },
      removeItem: (k: string) => { delete mem[k] },
      clear: () => { for (const k of Object.keys(mem)) delete mem[k] },
      key: (i: number) => Object.keys(mem)[i] ?? null,
      get length() { return Object.keys(mem).length },
    },
  })
}
ensureLocalStorage()

let n = 0
if (!('createObjectURL' in URL)) Object.defineProperty(URL, 'createObjectURL', { writable: true, value: () => `blob:test/${++n}` })
else URL.createObjectURL = () => `blob:test/${++n}`
URL.revokeObjectURL = () => undefined
Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, writable: true, value: () => Promise.resolve() })
Object.defineProperty(window, 'isSecureContext', { configurable: true, writable: true, value: true })
// Startup auth check: no saved sign-in in tests.
globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ error: { code: 'UNAUTHORIZED', message: 'no' } }), { status: 401, headers: { 'Content-Type': 'application/json' } })) as typeof fetch

afterEach(() => { cleanup(); vi.restoreAllMocks(); ensureLocalStorage() })
