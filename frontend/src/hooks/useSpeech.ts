import { useSyncExternalStore } from 'react'
import { speech } from '../services/speech'

/** True while FixSaathi is preparing or reading a reply aloud. */
export function useSpeaking() {
  return useSyncExternalStore(cb => speech.subscribe(cb), () => speech.isSpeaking(), () => false)
}

/** Diagnostics: the last personal-voice failure (server VOICE_STRICT), or null. */
export function useVoiceError() {
  return useSyncExternalStore(cb => speech.subscribe(cb), () => speech.error(), () => null)
}

/** 'preparing' while the natural voice is being generated, then 'speaking'; and which engine is speaking. */
export function useSpeechPhase() {
  const phase = useSyncExternalStore(cb => speech.subscribe(cb), () => speech.phase(), () => 'idle' as const)
  const engine = useSyncExternalStore(cb => speech.subscribe(cb), () => speech.engine(), () => null)
  return { phase, engine }
}
