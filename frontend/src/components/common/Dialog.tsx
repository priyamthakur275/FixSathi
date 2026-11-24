import { useEffect, useRef, type ReactNode, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

/** Closes a popover on an outside click or Escape. */
export function useDismiss(open: boolean, refs: RefObject<HTMLElement | null>[], onClose: () => void) {
  useEffect(() => {
    if (!open) return
    const down = (e: MouseEvent | TouchEvent) => { if (!refs.some(r => r.current?.contains(e.target as Node))) onClose() }
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('mousedown', down); document.addEventListener('touchstart', down); document.addEventListener('keydown', key)
    return () => { document.removeEventListener('mousedown', down); document.removeEventListener('touchstart', down); document.removeEventListener('keydown', key) }
  }, [open, refs, onClose])
}

interface ConfirmProps {
  open: boolean; title: string; body: ReactNode; confirm: string; cancel: string; busy?: boolean; danger?: boolean
  onConfirm: () => void; onCancel: () => void
}

/** A small modal confirmation. Focus starts on Cancel, so Enter never deletes by accident. */
export function ConfirmDialog({ open, title, body, confirm, cancel, busy, danger, onConfirm, onCancel }: ConfirmProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    const t = setTimeout(() => cancelRef.current?.focus(), 0)
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape' && !busy) onCancel() }
    document.addEventListener('keydown', key)
    return () => { clearTimeout(t); document.removeEventListener('keydown', key) }
  }, [open, busy, onCancel])
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-body">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-black/55 backdrop-blur-[2px]" onClick={() => !busy && onCancel()} />
          <motion.div initial={{ opacity: 0, scale: 0.97, y: 6 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.97 }} transition={{ duration: 0.15 }}
            className="popover relative w-full max-w-sm p-5">
            <h2 id="confirm-title" className="text-base font-semibold">{title}</h2>
            <div id="confirm-body" className="mt-2 text-sm leading-relaxed text-ink-2">{body}</div>
            <div className="mt-5 flex justify-end gap-2">
              <button ref={cancelRef} onClick={onCancel} disabled={busy} className="btn">{cancel}</button>
              <button onClick={onConfirm} disabled={busy} className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}>{busy && <Loader2 size={14} className="animate-spin" />}{confirm}</button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
