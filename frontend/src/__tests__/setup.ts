// Shared browser stubs for component tests (jsdom has no media, object URLs or layout).
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

let n = 0
if (!('createObjectURL' in URL)) Object.defineProperty(URL, 'createObjectURL', { writable: true, value: () => `blob:test/${++n}` })
else URL.createObjectURL = () => `blob:test/${++n}`
URL.revokeObjectURL = () => undefined
Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, writable: true, value: () => Promise.resolve() })
Object.defineProperty(window, 'isSecureContext', { configurable: true, writable: true, value: true })
// Startup auth check: no saved sign-in in tests.
globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ error: { code: 'UNAUTHORIZED', message: 'no' } }), { status: 401, headers: { 'Content-Type': 'application/json' } })) as typeof fetch

afterEach(() => { cleanup(); vi.restoreAllMocks() })
