/**
 * Service layer. Every UI screen talks to the FastAPI backend only through these functions.
 * There are no mock implementations: when AI is not configured on the server the API returns AI_NOT_CONFIGURED and the UI says so.
 */
import { api, apiBase, refreshDetailed, tokens } from './api'
import type {
  ChatResult, ComponentResult, Diagnosis, Escalation, FileKind, Language, MediaItem, NameplateResponse, Overview, Page, RepairSession, RepairStep, Report, SafetyState,
  SavedDiagnosis, ServerMessage, SimilarResult, TechRow, Tokens, TrendPoint, User,
} from '../types'

export const authService = {
  async login(email: string, password: string): Promise<User> {
    const t = await api<Tokens>('/api/v1/auth/login', { body: { email, password } }); tokens.set(t.access_token, t.refresh_token); return t.user
  },
  async register(full_name: string, email: string, password: string, organisation_name?: string): Promise<User> {
    const t = await api<Tokens>('/api/v1/auth/register', { body: { full_name, email, password, organisation_name: organisation_name || null } })
    tokens.set(t.access_token, t.refresh_token); return t.user
  },
  currentUser: () => api<User>('/api/v1/auth/me'),
  async logout() { const rt = tokens.refresh(); if (rt) await api('/api/v1/auth/logout', { body: { refresh_token: rt } }).catch(() => undefined); tokens.clear() },
  updateMe: (patch: { full_name?: string; preferred_language?: Language }) => api<User>('/api/v1/users/me', { method: 'PATCH', body: patch }),
}

export const sessionService = {
  create: (issue_description: string, appliance_type?: string) => api<RepairSession>('/api/v1/sessions', { body: { issue_description, appliance_type: appliance_type || null } }),
  get: (id: string) => api<RepairSession>(`/api/v1/sessions/${id}`),
  list: (limit = 20, status?: string) => api<Page<RepairSession>>(`/api/v1/sessions?limit=${limit}${status ? `&status=${status}` : ''}`),
  /** The technician's own chat history (newest first), optionally filtered by a search over titles and message text. */
  mine: (q = '', limit = 100) => api<Page<RepairSession>>(`/api/v1/sessions?mine=true&limit=${limit}${q.trim() ? `&q=${encodeURIComponent(q.trim())}` : ''}`),
  rename: (id: string, title: string) => api<RepairSession>(`/api/v1/sessions/${id}`, { method: 'PATCH', body: { title } }),
  /** Removes the chat from the history. Reports and safety records are kept on the server. */
  remove: (id: string) => api<null>(`/api/v1/sessions/${id}`, { method: 'DELETE' }),
  /** Thumbs up / down on one AI answer; null clears it. The optional note says what was wrong. */
  rateAnswer: (sid: string, mid: string, helpful: boolean | null, comment?: string) =>
    api<ServerMessage>(`/api/v1/sessions/${sid}/messages/${mid}/feedback`, { method: 'PUT', body: { helpful, comment: comment || null } }),
  cancel: (id: string) => api<RepairSession>(`/api/v1/sessions/${id}/cancel`, { method: 'POST' }),
  /** Downloads the repair report PDF for a conversation, built on the server from its recorded data. */
  async downloadPdf(id: string, reference?: string) {
    const r = await api<Response>(`/api/v1/sessions/${id}/report.pdf`, { raw: true, timeoutMs: 60000 })
    const url = URL.createObjectURL(await r.blob())
    const a = document.createElement('a'); a.href = url; a.download = `FixSaathi-${reference || id.slice(0, 8)}-repair-report.pdf`; a.rel = 'noopener'
    document.body.appendChild(a); a.click(); a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  },
}

export interface DemoScenario { id: string; title: string; appliance: string; issue: string; has_photo: boolean }
export const demoService = {
  list: () => api<{ label: string; items: DemoScenario[] }>('/api/v1/demo/scenarios'),
  start: (scenario: string) => api<RepairSession>('/api/v1/demo/sessions', { body: { scenario }, timeoutMs: 30000 }),
}

export class StreamFallbackError extends Error {
  constructor(message = 'Streaming unavailable') { super(message); this.name = 'StreamFallbackError' }
}

export interface ChatStreamCallbacks {
  onUserMessage?: (m: ServerMessage) => void
  onDelta?: (chunk: string) => void
  onDone?: (m: ServerMessage) => void
  onAiError?: (status: 'unavailable' | 'error', err: { code: string; message: string; hint?: string | null }) => void
}

export const chatService = {
  history: (sid: string) => api<Page<ServerMessage>>(`/api/v1/sessions/${sid}/messages?limit=200`),
  send: (sid: string, text: string, media_ids: string[], channel: 'text' | 'voice' = 'text') => api<ChatResult>(`/api/v1/sessions/${sid}/messages`, { body: { text, media_ids, channel }, timeoutMs: 90000 }),
  async stream(sid: string, text: string, media_ids: string[], channel: 'text' | 'voice', cb: ChatStreamCallbacks, signal?: AbortSignal): Promise<void> {
    const runFetch = () => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json', Accept: 'text/event-stream' }
      const access = tokens.access()
      if (access) headers.Authorization = `Bearer ${access}`
      return fetch(`${apiBase}/api/v1/sessions/${sid}/messages/stream`, {
        method: 'POST', headers, body: JSON.stringify({ text, media_ids, channel }), signal,
      })
    }
    let res: Response
    try {
      res = await runFetch()
      if (res.status === 401 && (await refreshDetailed()) === 'ok') res = await runFetch()
    } catch (e) {
      if ((e as Error)?.name === 'AbortError') throw e
      throw new StreamFallbackError((e as Error)?.message || 'Network stream error')
    }
    const ct = res.headers.get('content-type') || ''
    if (!res.ok || !ct.includes('text/event-stream') || !res.body) {
      throw new StreamFallbackError(`Stream HTTP ${res.status}`)
    }
    const reader = res.body.getReader()
    const dec = new TextDecoder()
    let buf = ''
    let gotDoneOrError = false
    const handleEvent = (raw: string) => {
      let ev = 'message'
      const dataLines: string[] = []
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) ev = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
      }
      if (!dataLines.length) return
      const payload = JSON.parse(dataLines.join('\n')) as Record<string, unknown>
      if (ev === 'user_message' && payload.user_message) cb.onUserMessage?.(payload.user_message as ServerMessage)
      else if (ev === 'delta' && typeof payload.text === 'string') cb.onDelta?.(payload.text)
      else if (ev === 'done' && payload.assistant_message) { gotDoneOrError = true; cb.onDone?.(payload.assistant_message as ServerMessage) }
      else if (ev === 'error') {
        gotDoneOrError = true
        cb.onAiError?.((payload.ai_status as 'unavailable' | 'error') || 'error', (payload.ai_error as { code: string; message: string; hint?: string | null }) || { code: 'AI_ERROR', message: 'The AI could not reply.' })
      }
    }
    while (true) {
      const { value, done } = await reader.read()
      if (value) buf += dec.decode(value, { stream: !done })
      else if (done) buf += dec.decode()
      buf = buf.replace(/\r\n/g, '\n')
      let sep = buf.indexOf('\n\n')
      while (sep !== -1) {
        const block = buf.slice(0, sep)
        buf = buf.slice(sep + 2)
        if (block.trim()) handleEvent(block)
        sep = buf.indexOf('\n\n')
      }
      if (done) {
        if (buf.trim()) handleEvent(buf)
        break
      }
    }
    if (!gotDoneOrError) throw new Error('Stream ended unexpectedly before finishing.')
  },
}

/** Every file the technician can attach. The server checks the real bytes again; this check gives a fast, clear message. */
export const FILE_RULES = {
  imageTypes: ['image/jpeg', 'image/png', 'image/webp'],
  imageExt: ['jpg', 'jpeg', 'png', 'webp'],
  docExt: ['pdf', 'docx', 'txt', 'csv', 'md', 'log'],
  maxImageBytes: 8 * 1024 * 1024,
  maxDocBytes: 15 * 1024 * 1024,
  maxPerMessage: 6,
  acceptImages: 'image/jpeg,image/png,image/webp',
  acceptDocs: '.pdf,.docx,.txt,.csv,.md,.log,application/pdf,text/plain,text/csv,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}
const extOf = (name: string) => (name.includes('.') ? name.split('.').pop()!.toLowerCase() : '')
export const fmtSize = (n: number) => n < 1024 ? `${n} B` : n < 1024 * 1024 ? `${Math.round(n / 1024)} KB` : `${(n / (1024 * 1024)).toFixed(1)} MB`

export const fileService = {
  /** image | document, or an error message for anything unsupported or too large. */
  check(file: File | Blob): { kind: FileKind } | { error: string } {
    const name = file instanceof File ? file.name : 'camera-photo.jpg'
    const ext = extOf(name)
    const isImage = FILE_RULES.imageTypes.includes(file.type) || (!file.type && FILE_RULES.imageExt.includes(ext))
    const isDoc = FILE_RULES.docExt.includes(ext) || file.type === 'application/pdf'
    if (file.size === 0) return { error: `“${name}” is empty.` }
    if (isImage) return file.size > FILE_RULES.maxImageBytes ? { error: `“${name}” is larger than 8 MB. Please choose a smaller photo.` } : { kind: 'image' }
    if (isDoc) return file.size > FILE_RULES.maxDocBytes ? { error: `“${name}” is larger than 15 MB. Upload only the pages you need.` } : { kind: 'document' }
    if (file.type.startsWith('image/')) return { error: `“${name}” is not supported. Use a JPG, PNG or WebP photo.` }
    return { error: `“${name}” is not a supported file. Use photos (JPG, PNG, WebP), PDF, Word (.docx) or text files.` }
  },
  upload(sid: string, file: Blob, source: 'upload' | 'capture', name?: string) {
    const f = new FormData(); f.append('file', file, name || (file instanceof File ? file.name : source === 'capture' ? 'camera-photo.jpg' : 'upload'))
    return api<MediaItem>(`/api/v1/sessions/${sid}/files?source=${source}`, { form: f, timeoutMs: 90000 })
  },
  list: (sid: string) => api<MediaItem[]>(`/api/v1/sessions/${sid}/images`),
}

/** Kept for older call sites: photo-only validation and upload. */
export const cameraService = {
  maxBytes: FILE_RULES.maxImageBytes,
  validate(file: File | Blob): string | null {
    if (!file.type.startsWith('image/')) return 'That file is not an image. Please choose a JPG, PNG or WebP photo.'
    if (!FILE_RULES.imageTypes.includes(file.type)) return 'That image type is not supported. Please choose a JPG, PNG or WebP photo.'
    if (file.size > cameraService.maxBytes) return 'That image is larger than 8 MB. Please choose a smaller one.'
    return null
  },
  upload: (sid: string, file: Blob, source: 'upload' | 'capture') => fileService.upload(sid, file, source),
  list: fileService.list,
}

export const repairService = {
  diagnose: (sid: string, media_ids: string[] = []) => api<Diagnosis>(`/api/v1/sessions/${sid}/diagnose`, { body: { media_ids }, timeoutMs: 90000 }),
  diagnosis: (sid: string) => api<Diagnosis | null>(`/api/v1/sessions/${sid}/diagnosis`),
  steps: (sid: string) => api<RepairStep[]>(`/api/v1/sessions/${sid}/steps`),
  generateSteps: (sid: string) => api<RepairStep[]>(`/api/v1/sessions/${sid}/steps/generate`, { method: 'POST', timeoutMs: 90000 }),
  completeStep: (sid: string, stepId: string) => api<RepairStep>(`/api/v1/sessions/${sid}/steps/${stepId}/complete`, { method: 'POST' }),
  reopenStep: (sid: string, stepId: string) => api<RepairStep>(`/api/v1/sessions/${sid}/steps/${stepId}/reopen`, { method: 'POST' }),
  stepVisual: (sid: string, stepId: string) => api<MediaItem>(`/api/v1/sessions/${sid}/steps/${stepId}/visual`, { method: 'POST', timeoutMs: 120000 }),
  identify: (sid: string, media_id: string, query?: string) => api<ComponentResult>(`/api/v1/sessions/${sid}/identify-component`, { body: { media_id, query: query || null }, timeoutMs: 90000 }),
  readNameplate: (sid: string, media_id: string) => api<NameplateResponse>(`/api/v1/sessions/${sid}/read-nameplate`, { body: { media_id }, timeoutMs: 90000 }),
  updateNameplate: (sid: string, patch: { appliance_type?: string | null; brand?: string | null; model?: string | null; error_code?: string | null; serial_number?: string | null }) =>
    api<NameplateResponse>(`/api/v1/sessions/${sid}/nameplate`, { method: 'PATCH', body: patch }),
  safety: (sid: string) => api<SafetyState>(`/api/v1/sessions/${sid}/safety`),
  confirmSafety: (sid: string, power_off_confirmed: boolean, tester_checked: boolean) => api<SafetyState>(`/api/v1/sessions/${sid}/safety/confirm`, { body: { power_off_confirmed, tester_checked } }),
  escalate: (sid: string, reason: string, priority = 'normal') => api<Escalation>(`/api/v1/sessions/${sid}/escalate`, { body: { reason, priority } }),
  similar: (sid: string) => api<SimilarResult>(`/api/v1/sessions/${sid}/similar-repairs`),
  feedback: (sid: string, rating: number, guidance_correct: boolean | null) => api(`/api/v1/sessions/${sid}/feedback`, { body: { rating, guidance_correct } }),
  report: (sid: string, outcome: 'resolved' | 'not_resolved' | 'escalated', first_time_fix: boolean | null, notes: string) =>
    api<Report>(`/api/v1/sessions/${sid}/reports`, { body: { outcome, first_time_fix, notes: notes || null } }),
}

export const historyService = {
  list: (openOnly = false) => api<Page<RepairSession>>(`/api/v1/history?limit=50${openOnly ? '&open_only=true' : ''}`),
  reports: () => api<Page<Report>>('/api/v1/reports?limit=50'),
  report: (id: string) => api<Report>(`/api/v1/reports/${id}`),
  diagnoses: () => api<SavedDiagnosis[]>('/api/v1/diagnoses'),
  escalations: () => api<Escalation[]>('/api/v1/escalations'),
  updateEscalation: (id: string, status: string, resolution_notes?: string) => api<Escalation>(`/api/v1/escalations/${id}`, { method: 'PATCH', body: { status, resolution_notes } }),
}

export const dashboardService = {
  async load() {
    const [overview, trend, technicians, metrics] = await Promise.all([
      api<Overview>('/api/v1/dashboard/overview'), api<TrendPoint[]>('/api/v1/dashboard/repairs?days=7'),
      api<TechRow[]>('/api/v1/dashboard/technicians'), api<{ ratings: { stars: string; count: number }[] }>('/api/v1/dashboard/metrics'),
    ])
    return { overview, trend, technicians, ratings: metrics.ratings }
  },
}

export interface LookupStep { text: string | null; locked: boolean }
export interface LookupResult {
  record_id: string; title: string; appliance_type: string; appliance_label: string; brand: string | null; model: string | null; error_code: string | null
  symptoms: string[]; possible_faults: string[]; components: string[]; steps: LookupStep[]; locked_steps: number; safety: string[]; severity: string | null
  match: 'error_code' | 'keyword' | 'embedding' | 'filter'; related_category: boolean; source_name: string; source_url: string | null; license: string; verification_status: string
}
export interface LookupResponse { query: string; appliance_type: string | null; brand: string | null; error_codes_found: string[]; error_codes_unknown: string[]; coverage: string; results: LookupResult[] }
/** Fault finder: error codes and symptoms looked up in the sourced records, without the AI. */
export const lookupService = {
  search: (q: string, appliance?: string | null) => api<LookupResponse>(`/api/v1/lookup?q=${encodeURIComponent(q)}${appliance ? `&appliance_type=${appliance}` : ''}`),
}

export interface KnowledgeStats { total: number; by_category: Record<string, number>; by_verification_status: Record<string, number> }
export interface AiStatus { configured: boolean; models: Record<string, string | null> }
export interface EvalMetrics { cases: number; 'hit@1': number; 'hit@3': number; 'hit@6': number; mrr: number }
export interface EvalMissTop3 { id: string; query: string; rank: number; top3: string[] }
export interface EvalDetectionMiss { id: string; query: string; expected: string; got: string }
export interface EvalSplit {
  overall: EvalMetrics
  by_language: Record<string, EvalMetrics>
  by_appliance: Record<string, EvalMetrics>
  misses_top3: EvalMissTop3[]
}
export interface EvalRetrievalSuite {
  appliance_selected: EvalSplit
  appliance_detected: EvalSplit
  appliance_detection_accuracy: number
  appliance_detection_misses: EvalDetectionMiss[]
}
export interface EvalSafetyError { id: string; text: string; expected: string; withheld: boolean }
export interface EvalSafetySuite {
  cases: number
  unsafe_withheld: string
  recall_unsafe: number
  safe_shown: string
  false_positive_rate: number
  errors: EvalSafetyError[]
}
export interface EvaluationResults {
  date: string
  retrieval_channels: string
  note: string
  development: { retrieval: EvalRetrievalSuite; safety_filter: EvalSafetySuite }
  held_out: { retrieval: EvalRetrievalSuite; safety_filter: EvalSafetySuite }
  held_out_v2: { retrieval: EvalRetrievalSuite }
}
export const systemService = {
  knowledge: () => api<KnowledgeStats>('/api/v1/knowledge/stats'),
  ai: () => api<AiStatus>('/api/v1/ai/status'),
  evaluation: () => api<EvaluationResults>('/api/v1/evaluation'),
}
