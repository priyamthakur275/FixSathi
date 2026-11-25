import { useEffect, useRef, useState, type ClipboardEvent, type DragEvent, type FormEvent, type KeyboardEvent } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUp, Camera, Check, FileText, ImagePlus, Loader2, Mic, Paperclip, Plus, Square, Volume2, VolumeX, X } from 'lucide-react'
import { CameraModal } from '../camera/CameraModal'
import { LiveWaveform } from '../voice/Waveform'
import { useSpeaking, useSpeechPhase, useVoiceError } from '../../hooks/useSpeech'
import { FILE_RULES, fileService, fmtSize } from '../../services'
import { speech } from '../../services/speech'
import { useApp } from '../../context/AppContext'
import { usePrefs } from '../../context/PrefsContext'
import { useDictation } from '../../hooks/useDictation'
import { useLanguage, useT, type Key } from '../../i18n'
import type { Attachment } from '../../types'

interface Props { onSend: (text: string, attachments: Attachment[], channel?: 'text' | 'voice') => void; disabled?: boolean; autoFocus?: boolean; initial?: string; compact?: boolean }

const uid = () => Math.random().toString(36).slice(2, 10)

/** A file chip for a document (PDF, Word, text). */
export function DocChip({ name, size, onRemove, onOpen }: { name: string; size?: number; onRemove?: () => void; onOpen?: () => void }) {
  const ext = name.includes('.') ? name.split('.').pop()!.toUpperCase() : 'FILE'
  const body = (
    <>
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${ext === 'PDF' ? 'bg-crit/12 text-crit' : ext === 'DOCX' ? 'bg-blue/12 text-blue' : 'bg-teal/12 text-teal'}`}><FileText size={16} /></span>
      <span className="min-w-0"><span className="block truncate text-[13px] font-medium text-ink">{name}</span><span className="block text-[11px] text-ink-3">{ext}{size ? ` · ${fmtSize(size)}` : ''}</span></span>
    </>
  )
  const cls = 'relative inline-flex max-w-[240px] items-center gap-2.5 rounded-xl border border-line bg-surface-2 py-2 pl-2.5 pr-3 text-left'
  return (
    <span className="relative inline-flex">
      {onOpen ? <button type="button" onClick={onOpen} title={`Open ${name}`} className={`${cls} transition-colors hover:border-line-2`}>{body}</button> : <span className={cls}>{body}</span>}
      {onRemove && <button type="button" aria-label={`Remove ${name}`} onClick={onRemove} className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-surface-3 text-ink ring-1 ring-line-2 hover:bg-crit hover:text-white"><X size={11} /></button>}
    </span>
  )
}

/** Speaker on/off. Off means replies are text only; the microphone keeps working. */
export function SpeakerToggle({ className = '' }: { className?: string }) {
  const t = useT()
  const { speaker, setSpeaker } = usePrefs()
  const label = speaker ? t('voice.speakerOn') : t('voice.speakerOff')
  return (
    <button type="button" onClick={() => { if (speaker) speech.stop(); setSpeaker(!speaker) }} aria-pressed={speaker} aria-label={label} title={label}
      className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${speaker ? 'text-accent hover:bg-accent/10' : 'text-ink-3 hover:bg-surface-2 hover:text-ink'} ${className}`}>
      {speaker ? <Volume2 size={18} /> : <VolumeX size={18} />}
    </button>
  )
}

export function Composer({ onSend, disabled, autoFocus, compact }: Props) {
  const t = useT()
  const language = useLanguage()
  const { draft, clearDraft } = useApp()
  const [text, setText] = useState('')
  const [files, setFiles] = useState<Attachment[]>([])
  const [camera, setCamera] = useState(false)
  const [menu, setMenu] = useState(false)
  const [drag, setDrag] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const imgInput = useRef<HTMLInputElement>(null)
  const docInput = useRef<HTMLInputElement>(null)
  const area = useRef<HTMLTextAreaElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const plusRef = useRef<HTMLButtonElement>(null)
  const dict = useDictation(language)
  const speaking = useSpeaking()
  const { phase, engine } = useSpeechPhase()
  const vErr = useVoiceError()
  const [voiceErr, setVoiceErr] = useState<string | null>(null)
  const canSend = !disabled && (text.trim().length > 0 || files.length > 0)

  // Grow with the text up to a limit, like a modern chat box.
  useEffect(() => {
    const el = area.current; if (!el) return
    el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [text])

  // A message that failed to upload or send comes back here, so nothing typed or attached is lost.
  // The text and files are restored while rendering (no extra render pass); clearing the draft and focusing are effects.
  const [restored, setRestored] = useState<typeof draft>(null)
  if (draft && draft !== restored) { setRestored(draft); setText(draft.text); setFiles(draft.attachments) }
  useEffect(() => {
    if (!draft) return
    clearDraft(); area.current?.focus()
  }, [draft, clearDraft])
  const shownVoiceErr = voiceErr ?? dict.error

  // Close the attach menu on outside click or Escape; move focus into it when it opens.
  useEffect(() => {
    if (!menu) return
    const onDown = (e: MouseEvent) => { if (!menuRef.current?.contains(e.target as Node) && !plusRef.current?.contains(e.target as Node)) setMenu(false) }
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === 'Escape') { setMenu(false); plusRef.current?.focus() } }
    document.addEventListener('mousedown', onDown); document.addEventListener('keydown', onKey)
    const tm = setTimeout(() => menuRef.current?.querySelector<HTMLButtonElement>('[role=menuitem]')?.focus(), 0)
    return () => { clearTimeout(tm); document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [menu])

  const add = (list: (File | Attachment)[]) => {
    const errs: string[] = []
    const next = [...files]
    for (const it of list) {
      if (next.length >= FILE_RULES.maxPerMessage) { errs.push(`You can attach up to ${FILE_RULES.maxPerMessage} files per message.`); break }
      if (!(it instanceof File) && 'kind' in it) { next.push(it); continue }
      const f = it as File
      const c = fileService.check(f)
      if ('error' in c) { errs.push(c.error); continue }
      next.push({ id: uid(), name: f.name, url: URL.createObjectURL(f), source: 'upload', kind: c.kind, size: f.size, file: f })
    }
    setFiles(next); setErrors([...new Set(errs)])
  }
  const remove = (id: string) => { const x = files.find(f => f.id === id); if (x) URL.revokeObjectURL(x.url); setFiles(files.filter(f => f.id !== id)) }

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (!canSend) return
    speech.stop()
    onSend(text, files, 'text'); setText(''); setFiles([]); setErrors([])
  }
  const key = (e: KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit() } }
  const paste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const pasted = Array.from(e.clipboardData?.files ?? [])
    if (pasted.length) { e.preventDefault(); add(pasted) }
  }
  const drop = (e: DragEvent) => { e.preventDefault(); setDrag(false); const d = Array.from(e.dataTransfer?.files ?? []); if (d.length) add(d) }
  const pick = (input: HTMLInputElement) => { add(Array.from(input.files ?? [])); input.value = '' }
  const choose = (what: 'images' | 'docs' | 'camera') => {
    setMenu(false)
    if (what === 'camera') setCamera(true)
    else (what === 'images' ? imgInput : docInput).current?.click()
  }

  // Voice: Start opens the microphone; nothing is sent until Done. Done stops the microphone, waits for the final words and sends.
  const startVoice = () => { setVoiceErr(null); dict.clearError(); if (!dict.supported) { setVoiceErr('unsupported'); return } void dict.start() }
  const finishVoice = async () => {
    const said = (await dict.done()).trim()
    const full = [text.trim(), said].filter(Boolean).join(' ')
    if (!full && !files.length) { setVoiceErr('empty'); return }
    onSend(full, files, 'voice'); setText(''); setFiles([]); setErrors([])
  }
  const voiceStatus = dict.state === 'starting' ? t('voice.starting') : dict.state === 'finishing' ? t('voice.finishing') : t('voice.listening')
  const item = 'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-ink transition-colors hover:bg-surface-2 focus:bg-surface-2 focus:outline-none'

  return (
    <>
      <AnimatePresence>
        {speaking && !dict.active && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} role="status"
            className="mx-auto mb-2 flex w-fit items-center gap-2.5 rounded-full border border-line bg-surface py-1 pl-3 pr-1 text-xs text-ink-2 shadow-sm">
            <span className="flex h-3 items-end gap-[2px]" aria-hidden>{[0, 1, 2, 3].map(i => <span key={i} className="w-[3px] rounded-full bg-accent" style={{ height: '100%', animation: `fs-wave ${0.6 + i * 0.12}s ease-in-out ${i * 0.08}s infinite` }} />)}</span>
            {phase === 'preparing' ? `${t('voice.preparing')}…` : <>{t('voice.speaking')}{engine && <span className="text-ink-3">· {t(engine === 'personal' ? 'voice.personalVoice' : engine === 'natural' ? 'voice.naturalVoice' : 'voice.deviceVoice')}</span>}</>}
            <button type="button" onClick={() => speech.stop()} aria-label={t('voice.stopSpeaking')} className="inline-flex items-center gap-1 rounded-full bg-surface-3 px-2.5 py-1 font-medium text-ink hover:bg-line-2"><Square size={10} fill="currentColor" />{t('voice.stop')}</button>
          </motion.div>
        )}
      </AnimatePresence>
      <div onDragOver={e => { e.preventDefault(); if (!drag) setDrag(true) }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDrag(false) }} onDrop={drop}
        className={`relative w-full rounded-[24px] border bg-surface transition-colors ${dict.active ? 'border-accent/60' : 'border-line-2 focus-within:border-ink-3/60'} ${compact ? 'shadow-[var(--shadow-card)]' : 'shadow-[var(--shadow-pop)]'}`}>
        {drag && <div className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center rounded-[24px] border-2 border-dashed border-accent bg-bg/85 text-sm font-medium text-accent"><Paperclip size={16} className="mr-2" />Drop photos or documents to attach</div>}
        <form onSubmit={submit} className="w-full p-2">
          {files.length > 0 && (
            <ul className="mb-1 flex flex-wrap gap-2 px-1.5 pt-1" aria-label="Attached files">
              {files.map(f => (
                <li key={f.id} className="relative">
                  {f.kind === 'image'
                    ? <><img src={f.url} alt={`Attachment ${f.name}`} className="h-16 w-16 rounded-xl border border-line object-cover" />
                      <button type="button" aria-label={`Remove ${f.name}`} onClick={() => remove(f.id)} className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-surface-3 text-ink ring-1 ring-line-2 hover:bg-crit hover:text-white"><X size={11} /></button></>
                    : <DocChip name={f.name} size={f.size} onRemove={() => remove(f.id)} />}
                </li>
              ))}
            </ul>
          )}

          {dict.active ? (
            <div className="px-2.5 pb-1 pt-2" aria-live="polite">
              <p className={`min-h-[3.25rem] text-[15px] leading-relaxed ${dict.text ? 'text-ink' : 'text-ink-3'}`}>{[text.trim(), dict.text].filter(Boolean).join(' ') || t('voice.listenHint')}</p>
              <div className="mt-1 flex items-center gap-2">
                <button type="button" onClick={dict.cancel} aria-label={t('voice.cancel')} title={t('voice.cancel')} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink-2 hover:bg-surface-2 hover:text-ink"><X size={18} /></button>
                <span className="flex min-w-0 flex-1 items-center gap-2.5 overflow-hidden">
                  <span className="rec-pulse h-2.5 w-2.5 shrink-0 rounded-full bg-crit" aria-hidden />
                  <span className="shrink-0 text-xs font-medium text-ink-2" role="status">{voiceStatus}</span>
                  <LiveWaveform level={dict.level} className="min-w-0 flex-1 justify-end" />
                </span>
                <button type="button" onClick={() => void finishVoice()} disabled={dict.state !== 'listening'} aria-label={t('voice.done')}
                  className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full bg-[var(--color-accent-fill)] px-4 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50">
                  {dict.state === 'finishing' ? <Loader2 size={15} className="animate-spin" /> : <Check size={16} strokeWidth={2.6} />}{t('voice.done')}
                </button>
              </div>
            </div>
          ) : (<>
            <label className="sr-only" htmlFor="composer-input">Describe the appliance issue</label>
            <textarea id="composer-input" ref={area} maxLength={4000} value={text} onChange={e => setText(e.target.value)} onKeyDown={key} onPaste={paste} autoFocus={autoFocus} rows={compact ? 1 : 2}
              placeholder={compact ? t('composer.followup') : t('composer.placeholder')}
              className="block max-h-[200px] w-full resize-none bg-transparent px-3 py-2.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-ink-3" />
            <div className="flex items-center justify-between gap-2 px-0.5">
              <div className="relative flex items-center">
                <input ref={imgInput} id="attach-images" data-testid="attach-images" type="file" accept={FILE_RULES.acceptImages} multiple hidden onChange={e => pick(e.currentTarget)} />
                <input ref={docInput} id="attach-docs" data-testid="attach-docs" type="file" accept={FILE_RULES.acceptDocs} multiple hidden onChange={e => pick(e.currentTarget)} />
                <button ref={plusRef} type="button" aria-label="Add photos, documents or camera" aria-haspopup="menu" aria-expanded={menu} title="Attach photos, PDFs or documents, or use the camera"
                  onClick={() => setMenu(m => !m)} className={`flex h-9 w-9 items-center justify-center rounded-full transition-all ${menu ? 'rotate-45 bg-surface-3 text-ink' : 'text-ink-2 hover:bg-surface-2 hover:text-ink'}`}>
                  <Plus size={20} strokeWidth={2.2} />
                </button>
                <AnimatePresence>
                  {menu && (
                    <motion.div ref={menuRef} role="menu" aria-label="Attach" initial={{ opacity: 0, y: 6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 6, scale: 0.97 }} transition={{ duration: 0.14 }}
                      className="popover absolute bottom-11 left-0 z-30 w-[min(18rem,calc(100vw-3rem))] p-1.5">
                      <button role="menuitem" type="button" onClick={() => choose('images')} className={item}><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal/12 text-teal"><ImagePlus size={18} /></span><span><span className="block font-medium">Photos and images</span><span className="block text-xs text-ink-3">JPG, PNG, WebP · several at once</span></span></button>
                      <button role="menuitem" type="button" onClick={() => choose('docs')} className={item}><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-crit/12 text-crit"><FileText size={18} /></span><span><span className="block font-medium">PDF or document</span><span className="block text-xs text-ink-3">PDF, Word (.docx), TXT, CSV · up to 15 MB</span></span></button>
                      <button role="menuitem" type="button" onClick={() => choose('camera')} className={item}><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue/12 text-blue"><Camera size={18} /></span><span><span className="block font-medium">Take a photo</span><span className="block text-xs text-ink-3">Use your device camera</span></span></button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <div className="flex items-center gap-1">
                <SpeakerToggle />
                <button type="button" onClick={startVoice} disabled={disabled} aria-label={t('voice.start')} title={t('voice.start')}
                  className="flex h-9 w-9 items-center justify-center rounded-full text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink disabled:opacity-40"><Mic size={18} /></button>
                <button type="submit" disabled={!canSend} aria-label="Send" className="ml-0.5 flex h-9 w-9 items-center justify-center rounded-full bg-ink text-bg transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:bg-surface-3 disabled:text-ink-3">
                  {disabled && (text.trim() || files.length) ? <Loader2 size={17} className="animate-spin" /> : <ArrowUp size={18} strokeWidth={2.4} />}
                </button>
              </div>
            </div>
          </>)}
        </form>
      </div>
      {vErr && <p role="alert" className="mt-2 flex items-start justify-between gap-3 rounded-xl border border-crit/40 bg-crit/10 px-3 py-2 text-sm text-crit"><span><b>Your cloned voice did not play.</b> No other voice was used. {vErr.provider ?? 'elevenlabs'} · voice {vErr.voiceId ?? '?'} · HTTP {vErr.http ?? '?'} · {vErr.code}: {vErr.message}</span><button type="button" onClick={() => speech.clearError()} aria-label="Dismiss" className="shrink-0 text-ink-3 hover:text-ink"><X size={14} /></button></p>}
      {shownVoiceErr && <p role="alert" className="mt-2 flex items-start justify-between gap-3 rounded-xl border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">{t(`voice.err.${shownVoiceErr}` as Key)}<button type="button" onClick={() => { setVoiceErr(null); dict.clearError() }} aria-label="Dismiss" className="shrink-0 text-ink-3 hover:text-ink"><X size={14} /></button></p>}
      {errors.length > 0 && <div role="alert" className="mt-2 space-y-1 rounded-xl border border-crit/40 bg-crit/10 px-3 py-2 text-sm text-crit">{errors.map(e => <p key={e}>{e}</p>)}<button type="button" onClick={() => setErrors([])} className="text-xs text-ink-2 underline">Dismiss</button></div>}
      <CameraModal open={camera} onClose={() => setCamera(false)} onUse={a => add([a])} />
    </>
  )
}
