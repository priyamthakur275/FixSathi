export type Language = 'English' | 'Hindi' | 'Kannada' | 'Tamil'
export type Role = 'technician' | 'manager' | 'admin'

export interface User {
  id: string
  full_name: string
  email: string
  role: Role
  preferred_language: Language
  organisation_id: string | null
  organisation_name: string | null
  created_at: string
}

export interface Tokens { access_token: string; refresh_token: string; expires_in: number; user: User }

export type FileKind = 'image' | 'document'

export interface Attachment {
  id: string
  name: string
  /** Local preview URL (object URL). Never sent to the server. */
  url: string
  source: 'camera' | 'upload'
  /** image (shown as a thumbnail) or document (PDF, Word, text: shown as a file chip). */
  kind: FileKind
  size: number
  /** The bytes to upload. */
  file: Blob
}

/** What a chat message shows for each attached file. */
export interface MessageFile { id: string; url: string; server?: boolean; kind?: FileKind; name?: string; size?: number; mime?: string; pages?: number }

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  text: string
  at: number
  attachments?: MessageFile[]
  aiGenerated?: boolean
  demo?: boolean
  sources?: SourceRef[]
  notice?: 'ai_unavailable' | 'ai_error'
  hint?: string | null
  errorCode?: string
  /** A server-side action attached to the message, e.g. a repair report PDF ready to download. */
  action?: 'pdf_report'
  /** How the message being answered was sent. Only replies to voice messages are read aloud by themselves. */
  channel?: 'text' | 'voice'
  /** The technician's thumbs up (true) or down (false) on this AI answer; undefined when not rated. */
  helpful?: boolean
}

export type VoiceState = 'idle' | 'connecting' | 'listening' | 'processing' | 'responding' | 'error'
export type SessionStatus = 'created' | 'active' | 'diagnosing' | 'awaiting_confirmation' | 'guidance_in_progress' | 'escalated' | 'completed' | 'cancelled'

export interface RepairSession {
  id: string
  reference: string
  title: string
  appliance_type: string
  appliance_label: string
  demo?: boolean
  issue_description: string
  status: SessionStatus
  technician_id: string
  technician_name: string | null
  first_time_fix: boolean | null
  started_at: string
  completed_at: string | null
  report_id: string | null
}

export interface Page<T> { items: T[]; total: number; limit: number; offset: number }

export interface ServerMessage { id: string; role: 'user' | 'assistant' | 'system'; message: string; message_type: string; meta: Record<string, unknown>; created_at: string }
export interface ChatResult { user_message: ServerMessage; assistant_message: ServerMessage | null; ai_status: 'ok' | 'unavailable' | 'error'; ai_error: { code: string; message: string; hint?: string | null } | null }

export interface MediaItem { id: string; kind: 'capture' | 'upload' | 'generated' | 'document'; mime_type: string; size_bytes: number; width: number | null; height: number | null; url: string; meta: Record<string, unknown>; created_at: string }

export interface Evidence { source: 'observed_in_image' | 'technician_statement' | 'ai_inference' | 'unknown'; detail: string }
export interface Fault { fault: string; explanation: string; confidence: number; evidence: Evidence[]; status?: 'supported_by_records' | 'possible_cause' | 'unverified_hypothesis'; record_ids?: string[] }
export interface SourceRef { record_id: string; source_name: string; source_url: string | null; license: string; verification_status: string; match: string; related_category: boolean }
export interface Diagnosis {
  id: string; problem_summary: string; faults: Fault[]; recommended_checks: string[]; follow_up_questions: string[]; safety_requirements: string[]
  requires_escalation: boolean; model_identifier: string; created_at: string; confidence_note: string
  confirmed_findings: string[]; missing_information: string[]; required_tools?: string[]; escalation_reason?: string | null; knowledge_coverage: 'grounded' | 'partial' | 'none'; sources: SourceRef[]
}

export interface RepairStep {
  id: string; step_number: number; title: string; instruction: string | null
  kind: 'observation' | 'diagnostic_check' | 'safe_action' | 'power_sensitive' | 'escalation'
  requires_power_off: boolean; status: 'pending' | 'completed' | 'skipped'; locked: boolean; visual_media_id: string | null; completed_at: string | null
}

export interface SafetyState { power_off_confirmed: boolean; tester_checked: boolean; unlocked: boolean; missing: string[]; expired: boolean; confirmed_at: string | null; expires_at: string | null; disclaimer: string }

export interface Box { x_min: number; y_min: number; x_max: number; y_max: number }
export interface ComponentResult { id: string; media_id: string; found: boolean; component_name: string | null; explanation: string; box: Box | null; confidence: number; uncertainty: string | null; safety_warnings: string[]; note: string }

export interface Escalation { id: string; session_id: string; session_reference: string; appliance_type: string; technician: string | null; reason: string; priority: string; status: string; diagnosis_summary: string | null; resolution_notes: string | null; created_at: string; resolved_at: string | null }

export interface ReportData {
  demo?: boolean
  session: { reference: string; appliance: string; title: string; started_at: string; technician: string | null }
  customer_issue: string
  diagnosis: { problem_summary: string; faults: Fault[]; model_identifier: string; note: string } | null
  steps_performed: { step_number: number; title: string; completed_at: string | null }[]
  steps_not_performed: { step_number: number; title: string }[]
  parts_identified: { name: string | null; explanation: string | null }[]
  safety: { final_state: { power_off_confirmed: boolean; tester_checked: boolean; expired: boolean }; confirmation_events: { at: string; power_off_confirmed: boolean; tester_checked: boolean }[]; blocked_attempts: number; disclaimer: string }
  escalations: { reason: string; status: string }[]
  resolution: { outcome: string; first_time_fix: boolean | null; notes: string | null }
  feedback: { rating: number; guidance_correct: boolean | null; comment: string | null } | null
}
export interface Report { id: string; reference: string; session_id: string; session_reference: string; appliance: string; appliance_type: string; technician: string | null; resolution_status: string; created_at: string; title: string; data: ReportData }

export interface Overview {
  total_sessions: number; completed: number; active: number; escalated: number; open_escalations: number
  first_time_fix_rate: number | null; first_time_fix_sample: number; avg_repair_minutes: number | null; avg_rating: number | null; ratings_count: number
  guidance_correct_rate: number | null; answers_rated: number; answers_helpful: number; answer_helpful_rate: number | null; avg_ai_latency_ms: number | null; ai_cost_per_repair: number | null; ai_cost_note: string
}
export interface TrendPoint { day: string; date: string; sessions: number; completed: number }
export interface TechRow { name: string; sessions: number; escalated: number; completed: number }
export interface SimilarResult { mode: 'embeddings' | 'keyword'; fallback_reason: string | null; results: { source_type: 'session' | 'knowledge'; source_id: string; reference: string; report_id?: string; title: string; appliance_type: string; score: number; snippet: string; why: string }[] }
export interface SavedDiagnosis { id: string; session_id: string; reference: string; title: string; problem_summary: string; top_fault: Fault | null; created_at: string }
