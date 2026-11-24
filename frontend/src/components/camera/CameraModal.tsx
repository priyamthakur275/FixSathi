import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Camera, ImageUp, Loader2, RotateCcw, Send, SwitchCamera, VideoOff, X } from 'lucide-react'
import { cameraService } from '../../services'
import type { Attachment } from '../../types'

type Phase = 'loading' | 'live' | 'denied' | 'unavailable' | 'insecure' | 'busy' | 'captured'
interface Props { open: boolean; onClose: () => void; onUse: (a: Attachment) => void }

const MESSAGES: Record<'denied' | 'unavailable' | 'insecure' | 'busy', [string, string]> = {
  denied: ['Camera permission was denied', 'Allow camera access for this site in your browser settings (the camera icon in the address bar), then try again. Or use your phone camera app or upload a photo.'],
  unavailable: ['No camera found', 'This device or browser has no camera FixSaathi can open. You can use your phone camera app or upload a photo instead.'],
  insecure: ['Camera needs a secure connection', 'Browsers only allow the camera on https:// pages or localhost. Open FixSaathi over https, or upload a photo instead.'],
  busy: ['The camera is being used by another app', 'Close other apps or tabs using the camera (video calls, camera app), then try again.'],
}

/** "Show me the appliance": live preview, capture, review, then confirm. Nothing uploads until the message is sent. */
export function CameraModal({ open, onClose, onUse }: Props) {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const galleryInput = useRef<HTMLInputElement>(null)
  const nativeInput = useRef<HTMLInputElement>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [shot, setShot] = useState<string | null>(null)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [source, setSource] = useState<'camera' | 'upload'>('camera')
  const [facing, setFacing] = useState<'environment' | 'user'>('environment')
  const [canSwitch, setCanSwitch] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)

  const stop = useCallback(() => { stream.current?.getTracks().forEach(t => t.stop()); stream.current = null }, [])
  const dropShot = useCallback(() => { setShot(s => { if (s) URL.revokeObjectURL(s); return null }); setBlob(null) }, [])

  const start = useCallback(async (face: 'environment' | 'user' = 'environment') => {
    stop(); dropShot(); setPhase('loading'); setFileError(null)
    if (typeof window !== 'undefined' && window.isSecureContext === false) { setPhase('insecure'); return }
    if (!navigator.mediaDevices?.getUserMedia) { setPhase('unavailable'); return }
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: face }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      stream.current = s
      setPhase('live')
      try { setCanSwitch((await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput').length > 1) } catch { setCanSwitch(false) }
    } catch (e) {
      const name = (e as DOMException).name
      setPhase(name === 'NotAllowedError' || name === 'SecurityError' ? 'denied' : name === 'NotReadableError' || name === 'AbortError' ? 'busy' : 'unavailable')
    }
  }, [stop, dropShot])

  useEffect(() => {
    if (open) { setFacing('environment'); void start('environment') }
    else { stop(); dropShot() }
    return stop
  }, [open, start, stop, dropShot])

  useEffect(() => {
    if (phase === 'live' && video.current && stream.current) { video.current.srcObject = stream.current; void video.current.play().catch(() => undefined) }
  }, [phase])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey); return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const flip = () => { const f = facing === 'environment' ? 'user' : 'environment'; setFacing(f); void start(f) }

  const capture = () => {
    const v = video.current
    if (!v || !v.videoWidth) return
    const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight
    c.getContext('2d')?.drawImage(v, 0, 0)  // saved un-mirrored, as the camera sees the appliance
    c.toBlob(b => { if (b) { setBlob(b); setShot(URL.createObjectURL(b)); setSource('camera'); setPhase('captured'); stop() } }, 'image/jpeg', 0.9)
  }

  const onFile = (f: File | undefined, from: 'camera' | 'upload') => {
    if (!f) return
    const err = cameraService.validate(f)
    if (err) { setFileError(err); return }
    stop(); dropShot()
    setBlob(f); setShot(URL.createObjectURL(f)); setSource(from); setPhase('captured')
  }

  const use = () => {
    if (!shot || !blob) return
    const name = blob instanceof File ? blob.name : `camera-photo-${new Date().toISOString().slice(11, 19).replace(/:/g, '')}.jpg`
    onUse({ id: Math.random().toString(36).slice(2), name, url: shot, source, kind: 'image', size: blob.size, file: blob })
    setShot(null); setBlob(null)  // the preview URL now belongs to the attachment
    onClose()
  }
  const failed = phase === 'denied' || phase === 'unavailable' || phase === 'insecure' || phase === 'busy'

  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}
          className="fixed inset-0 z-[60] flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-6" role="dialog" aria-modal="true" aria-label="Show me the appliance">
          <motion.div initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }} className="flex max-h-[94dvh] w-full max-w-xl flex-col overflow-y-auto rounded-t-3xl border border-line-2 bg-bg-2 shadow-2xl sm:rounded-3xl">
            <div className="flex items-center justify-between px-5 py-4">
              <div><h2 className="font-semibold">Show me the appliance</h2><p className="text-xs text-ink-2">{phase === 'captured' ? 'Check the photo. It is added to your message; nothing is uploaded until you send.' : 'Point at the label, the fault or the part you are unsure about.'}</p></div>
              <button onClick={onClose} aria-label="Close camera" className="icon-btn h-9 w-9"><X size={18} /></button>
            </div>
            <div className="relative mx-5 flex aspect-[4/3] items-center justify-center overflow-hidden rounded-2xl border border-line bg-black">
              {phase === 'loading' && <div className="flex flex-col items-center gap-2 px-6 text-center text-ink-2"><Loader2 className="animate-spin" /><span className="text-sm">Starting the camera...</span><span className="text-xs text-ink-3">If your browser asks, choose Allow.</span></div>}
              {phase === 'live' && <video ref={video} playsInline muted aria-label="Live camera preview" className={`h-full w-full object-cover ${facing === 'user' ? '-scale-x-100' : ''}`} />}
              {phase === 'live' && canSwitch && <button onClick={flip} aria-label={facing === 'environment' ? 'Switch to front camera' : 'Switch to back camera'} className="absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur hover:bg-black/75"><SwitchCamera size={18} /></button>}
              {phase === 'captured' && shot && <img src={shot} alt="Captured appliance preview" className="h-full w-full object-contain" />}
              {failed && <div role="alert" className="max-w-sm p-6 text-center"><VideoOff className="mx-auto mb-2 text-warn" /><p className="text-sm font-medium">{MESSAGES[phase][0]}</p><p className="mt-1 text-xs leading-relaxed text-ink-2">{MESSAGES[phase][1]}</p></div>}
            </div>
            {fileError && <p role="alert" className="mx-5 mt-3 rounded-xl border border-crit/40 bg-crit/10 px-3 py-2 text-sm text-crit">{fileError}</p>}
            <div className="flex flex-wrap items-center justify-center gap-3 p-5">
              <input ref={galleryInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={e => { onFile(e.target.files?.[0], 'upload'); e.currentTarget.value = '' }} data-testid="camera-gallery" />
              <input ref={nativeInput} type="file" accept="image/*" capture="environment" hidden onChange={e => { onFile(e.target.files?.[0], 'camera'); e.currentTarget.value = '' }} data-testid="camera-native" />
              {phase === 'live' && <button onClick={capture} aria-label="Capture photo" className="fs-amber-bg flex h-16 w-16 items-center justify-center rounded-full text-white shadow-[0_10px_30px_-10px_rgba(255,138,43,.9)] ring-4 ring-white/10 transition-transform active:scale-95"><Camera /></button>}
              {phase === 'captured' && <>
                <button onClick={() => void start(facing)} className="btn"><RotateCcw size={16} />Retake</button>
                <button onClick={use} className="btn btn-primary px-5"><Send size={16} />Use this photo</button>
              </>}
              {failed && phase !== 'insecure' && <button onClick={() => void start(facing)} className="btn"><RotateCcw size={16} />Try camera again</button>}
              {failed && <button onClick={() => nativeInput.current?.click()} className="btn"><Camera size={16} />Use phone camera app</button>}
              {phase !== 'captured' && <button onClick={() => galleryInput.current?.click()} className="btn"><ImageUp size={16} />Upload from gallery</button>}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
