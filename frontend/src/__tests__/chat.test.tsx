import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { AuthProvider, useAuth } from '../context/AuthContext'
import { AppProvider, useApp } from '../context/AppContext'
import { PrefsProvider, usePrefs } from '../context/PrefsContext'
import { Composer } from '../components/composer/Composer'
import { DesktopSidebar } from '../components/sidebar/Sidebar'
import * as services from '../services'
import { chunks, pickVoice } from '../services/speech'
import { translate } from '../i18n'
import type { RepairSession } from '../types'

const wrap = (ui: ReactNode, path = '/') => render(
  <AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={[path]}><Routes><Route path="*" element={ui} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)

const day = (n: number) => new Date(Date.now() - n * 86400000).toISOString()
const chat = (id: string, title: string, ago: number) => ({ id, title, started_at: day(ago), reference: `FS-${id}`, status: 'active' }) as unknown as RepairSession
const page = (items: RepairSession[]) => ({ items, total: items.length, limit: 100, offset: 0 })

// ---------------- chat history ----------------

describe('chat history sidebar', () => {
  it('groups chats into Today, Yesterday, Previous 7 days and Older', async () => {
    vi.spyOn(services.sessionService, 'mine').mockResolvedValue(page([chat('a', 'Ceiling Fan Not Rotating', 0), chat('b', 'Split AC Error CH38', 1), chat('c', 'Refrigerator Cooling Problem', 4), chat('d', 'Washing Machine Not Draining', 30)]))
    wrap(<DesktopSidebar />)
    const nav = await screen.findByRole('navigation', { name: 'Chats' })
    await within(nav).findByText('Ceiling Fan Not Rotating')
    const labels = within(nav).getAllByText(/^(Today|Yesterday|Previous 7 days|Older)$/).map(e => e.textContent)
    expect(labels).toEqual(['Today', 'Yesterday', 'Previous 7 days', 'Older'])
    expect(within(nav).getByRole('link', { name: 'Split AC Error CH38' }).getAttribute('href')).toBe('/chat/b')
  })

  it('searches on the server', async () => {
    const u = userEvent.setup()
    const mine = vi.spyOn(services.sessionService, 'mine').mockImplementation(async (q = '') => page(q ? [chat('b', 'Split AC Error CH38', 1)] : [chat('a', 'Ceiling Fan', 0), chat('b', 'Split AC Error CH38', 1)]))
    wrap(<DesktopSidebar />)
    await screen.findByText('Ceiling Fan')
    await u.click(screen.getByRole('button', { name: 'Search chats' }))
    await u.type(screen.getByLabelText('Search chats'), 'ch38')
    await waitFor(() => expect(screen.queryByText('Ceiling Fan')).toBeNull())
    expect(mine).toHaveBeenLastCalledWith('ch38')
    expect(screen.getByText('Split AC Error CH38')).toBeTruthy()
  })

  it('renames a chat from its three-dot menu', async () => {
    const u = userEvent.setup()
    vi.spyOn(services.sessionService, 'mine').mockResolvedValue(page([chat('a', 'Fan', 0)]))
    const rename = vi.spyOn(services.sessionService, 'rename').mockResolvedValue(chat('a', 'Hall fan', 0))
    wrap(<DesktopSidebar />)
    await u.click(await screen.findByRole('button', { name: 'Chat options: Fan' }))
    await u.click(screen.getByRole('menuitem', { name: 'Rename' }))
    const box = screen.getByLabelText('Rename')
    await u.clear(box); await u.type(box, 'Hall fan{Enter}')
    expect(rename).toHaveBeenCalledTimes(1)
    expect(rename).toHaveBeenCalledWith('a', 'Hall fan')
    expect(await screen.findByRole('link', { name: 'Hall fan' })).toBeTruthy()
  })

  it('asks before deleting, and Cancel keeps the chat', async () => {
    const u = userEvent.setup()
    let deleted = false  // like the server: a deleted chat is no longer listed
    vi.spyOn(services.sessionService, 'mine').mockImplementation(async () => page(deleted ? [] : [chat('a', 'Fan', 0)]))
    const remove = vi.spyOn(services.sessionService, 'remove').mockImplementation(async () => { deleted = true; return null })
    wrap(<DesktopSidebar />)
    await u.click(await screen.findByRole('button', { name: 'Chat options: Fan' }))
    await u.click(screen.getByRole('menuitem', { name: 'Delete' }))
    const dialog = screen.getByRole('alertdialog', { name: 'Delete chat?' })
    expect(dialog.textContent).toMatch(/Service reports and safety records already saved are kept/)
    await u.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(remove).not.toHaveBeenCalled()
    await u.click(screen.getByRole('button', { name: 'Chat options: Fan' }))
    await u.click(screen.getByRole('menuitem', { name: 'Delete' }))
    await u.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete' }))
    expect(remove).toHaveBeenCalledWith('a')
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Fan' })).toBeNull())
  })
})

// ---------------- conversations never mix ----------------

function Probe() {
  const { send, newSession, messages, sessionId } = useApp()
  return <>
    <button onClick={() => void send('first chat question')}>send</button>
    <button onClick={() => newSession()}>new</button>
    <p data-testid="sid">{sessionId ?? 'none'}</p>
    <ul>{messages.map(m => <li key={m.id}>{m.role}:{m.text}</li>)}</ul>
  </>
}

describe('conversation isolation', () => {
  it('a reply that arrives after New chat is not shown in the new chat', async () => {
    const u = userEvent.setup()
    let reply!: (v: unknown) => void
    vi.spyOn(services.sessionService, 'create').mockResolvedValue({ id: 's1', title: 'x' } as never)
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({ id: 's1', title: 'x' } as never)
    vi.spyOn(services.chatService, 'send').mockImplementation(() => new Promise(r => { reply = r }) as never)
    wrap(<Probe />)
    await u.click(screen.getByRole('button', { name: 'send' }))
    await waitFor(() => expect(screen.getByTestId('sid').textContent).toBe('s1'))
    await u.click(screen.getByRole('button', { name: 'new' }))
    expect(screen.getByTestId('sid').textContent).toBe('none')
    const msg = (id: string, role: string, text: string) => ({ id, role, message: text, message_type: 'text', meta: {}, created_at: new Date().toISOString() })
    await act(async () => reply({ user_message: msg('u1', 'user', 'first chat question'), assistant_message: msg('a1', 'assistant', 'answer for chat one'), ai_status: 'ok', ai_error: null }))
    expect(screen.queryByText(/answer for chat one/)).toBeNull()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  })
})

// ---------------- voice input: start, speak, Done ----------------

class FakeRecognition {
  static last: FakeRecognition | null = null
  lang = ''; continuous = false; interimResults = false; maxAlternatives = 1
  onresult: ((e: unknown) => void) | null = null
  onend: (() => void) | null = null
  onerror: ((e: unknown) => void) | null = null
  started = 0
  constructor() { FakeRecognition.last = this }
  start() { this.started++ }
  stop() { setTimeout(() => this.onend?.(), 0) }
  abort() { setTimeout(() => this.onend?.(), 0) }
  hear(...parts: [string, boolean][]) { this.onresult?.({ results: parts.map(([t, f]) => Object.assign([{ transcript: t }], { isFinal: f })) }) }
}

function mockMic() {
  const track = { stop: vi.fn() }
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn(async () => ({ getTracks: () => [track] })) } })
  class AC { createAnalyser() { return { fftSize: 256, smoothingTimeConstant: 0, getByteTimeDomainData: (b: Uint8Array) => b.fill(128) } } createMediaStreamSource() { return { connect: () => undefined } } close() { return Promise.resolve() } }
  vi.stubGlobal('AudioContext', AC)
  return track
}

describe('voice input', () => {
  it('listens until Done, shows the words live, then sends the complete message once', async () => {
    const u = userEvent.setup()
    vi.stubGlobal('webkitSpeechRecognition', FakeRecognition)
    ;(window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition
    const track = mockMic()
    const { useDictation } = await import('../hooks/useDictation')
    void useDictation
    const sent: [string, string | undefined][] = []
    wrap(<Composer onSend={(t, _a, ch) => sent.push([t, ch])} />)
    await u.click(screen.getByRole('button', { name: 'Start speaking' }))
    await screen.findByRole('button', { name: 'Done' })
    const rec = FakeRecognition.last!
    expect(rec.continuous).toBe(true)
    act(() => rec.hear(['ceiling fan is', true], [' humming', false]))
    expect(screen.getByText('ceiling fan is humming')).toBeTruthy()
    act(() => rec.onend?.())  // the browser ends recognition after a pause: FixSaathi keeps listening, sends nothing
    expect(sent).toHaveLength(0)
    expect(rec.started + (FakeRecognition.last === rec ? 0 : 1)).toBeGreaterThan(0)
    act(() => FakeRecognition.last!.hear(['and not rotating', true]))
    await u.click(screen.getByRole('button', { name: 'Done' }))
    await waitFor(() => expect(sent).toHaveLength(1))
    expect(sent[0]).toEqual(['ceiling fan is humming and not rotating', 'voice'])
    expect(track.stop).toHaveBeenCalled()  // microphone released
    expect(screen.getByLabelText('Describe the appliance issue')).toBeTruthy()
  })

  it('Cancel discards what was heard', async () => {
    const u = userEvent.setup()
    ;(window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition
    mockMic()
    const sent: string[] = []
    wrap(<Composer onSend={t => sent.push(t)} />)
    await u.click(screen.getByRole('button', { name: 'Start speaking' }))
    await screen.findByRole('button', { name: 'Done' })
    act(() => FakeRecognition.last!.hear(['wrong words', true]))
    await u.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(sent).toHaveLength(0)
    expect(screen.queryByText('wrong words')).toBeNull()
  })
})

// ---------------- speaker, voice and theme preferences ----------------

function PrefsProbe() {
  const p = usePrefs()
  return <><button onClick={() => p.setTheme('light')}>light</button><button onClick={() => p.setTheme('dark')}>dark</button><p data-testid="spk">{String(p.speaker)}</p></>
}

describe('preferences', () => {
  it('the speaker toggle switches replies between spoken and text-only', async () => {
    const u = userEvent.setup()
    wrap(<><Composer onSend={() => undefined} /><PrefsProbe /></>)
    const on = screen.getByRole('button', { name: /Speaker on/ })
    expect(on.getAttribute('aria-pressed')).toBe('true')
    await u.click(on)
    expect(screen.getByRole('button', { name: /Speaker off/ }).getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByTestId('spk').textContent).toBe('false')
    expect(screen.getByRole('button', { name: 'Start speaking' })).toBeTruthy()  // the microphone still works with the speaker off
  })

  it('applies the theme to the page immediately', async () => {
    const u = userEvent.setup()
    wrap(<PrefsProbe />)
    await u.click(screen.getByRole('button', { name: 'light' }))
    expect(document.documentElement.dataset.theme).toBe('light')
    await u.click(screen.getByRole('button', { name: 'dark' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})

describe('speech helpers', () => {
  it('splits replies into short sentences without Markdown or citations', () => {
    const c = chunks('**Switch off** the MCB first [kb:fan-001]. Then check the capacitor.\n- Spin the blades by hand')
    expect(c).toEqual(['Switch off the MCB first.', 'Then check the capacitor.', 'Spin the blades by hand'])
    expect(chunks('word '.repeat(120)).every(x => x.length <= 220)).toBe(true)
  })

  it('prefers natural voices in the right language and never picks novelty voices', () => {
    const v = (name: string, lang: string) => ({ name, lang, voiceURI: name, localService: true, default: false }) as SpeechSynthesisVoice
    const all = [v('Albert', 'en-US'), v('Zarvox', 'en-US'), v('Rishi', 'en-IN'), v('Microsoft Neerja Online (Natural) - English (India)', 'en-IN'), v('Lekha', 'hi-IN')]
    vi.stubGlobal('speechSynthesis', { getVoices: () => all, cancel: () => undefined, speak: () => undefined })
    expect(pickVoice('English')?.name).toMatch(/Neerja/)
    expect(pickVoice('Hindi')?.name).toBe('Lekha')
    expect(pickVoice('English', 'Rishi')?.name).toBe('Rishi')
  })
})

describe('i18n', () => {
  it('translates the interface and falls back to English', () => {
    expect(translate('Hindi', 'nav.newChat')).toBe('नई चैट')
    expect(translate('Kannada', 'group.today')).toBe('ಇಂದು')
    expect(translate('Tamil', 'home.hello', { name: 'Ravi' })).toBe('வணக்கம், Ravi')
    expect(translate(undefined, 'nav.signOut')).toBe('Sign out')
  })
})

// ---------------- spoken replies: typed = text only, voice = spoken when the speaker is on ----------------

describe('text vs voice replies', () => {
  const msg = (id: string, role: string, text: string, channel: string) => ({ id, role, message: text, message_type: 'text', meta: { channel }, created_at: new Date().toISOString() })
  let n = 0
  let store: Record<string, string> = {}
  beforeEach(() => {
    store = {}
    vi.stubGlobal('localStorage', { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v }, removeItem: (k: string) => { delete store[k] } })
    Element.prototype.scrollIntoView = () => undefined  // not implemented by jsdom
    ;(window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition  // read when the composer renders
  })
  afterEach(() => { vi.unstubAllGlobals() })

  async function chatPage() {
    const { default: ChatPage } = await import('../pages/ChatPage')
    const { speech } = await import('../services/speech')
    vi.spyOn(services.sessionService, 'mine').mockResolvedValue(page([]))
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({ id: 's1', title: 'Fan', status: 'active' } as never)
    vi.spyOn(services.chatService, 'history').mockResolvedValue({ items: [], total: 0, limit: 200, offset: 0 } as never)
    vi.spyOn(services.chatService, 'send').mockImplementation(async (_sid, text, _m, channel = 'text') => {
      n++; return { user_message: msg(`u${n}`, 'user', text, channel), assistant_message: msg(`a${n}`, 'assistant', `Reply to ${text}`, channel), ai_status: 'ok', ai_error: null } as never
    })
    const speak = vi.spyOn(speech, 'speak').mockImplementation(() => undefined)
    // Like the app's protected routes: the chat renders once the sign-in check has finished.
    const Gate = () => (useAuth().loading ? null : <ChatPage />)
    render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter initialEntries={['/chat/s1']}><Routes><Route path="/chat/:id" element={<Gate />} /></Routes></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)
    await waitFor(() => expect(services.chatService.history).toHaveBeenCalled())
    return speak
  }

  async function type(u: ReturnType<typeof userEvent.setup>, text: string) {
    await u.type(await screen.findByLabelText('Describe the appliance issue'), text)
    await u.click(screen.getByRole('button', { name: 'Send' }))
    await screen.findByText(`Reply to ${text}`)
  }

  async function say(u: ReturnType<typeof userEvent.setup>, words: string) {
    mockMic()
    await u.click(await screen.findByRole('button', { name: 'Start speaking' }))
    await screen.findByRole('button', { name: 'Done' })
    act(() => FakeRecognition.last!.hear([words, true]))
    await u.click(screen.getByRole('button', { name: 'Done' }))
    await screen.findByText(`Reply to ${words}`)
  }

  it('an AI answer can be marked helpful or not, with a note on what was wrong', async () => {
    const u = userEvent.setup()
    await chatPage()
    vi.spyOn(services.chatService, 'send').mockResolvedValue({ user_message: msg('u9', 'user', 'fan slow', 'text'),
      assistant_message: { ...msg('a9', 'assistant', 'Reply to fan slow', 'text'), meta: { ai_generated: true } }, ai_status: 'ok', ai_error: null } as never)
    const rate = vi.spyOn(services.sessionService, 'rateAnswer').mockResolvedValue({} as never)
    await type(u, 'fan slow')
    await u.click(screen.getByRole('button', { name: 'Not helpful' }))
    expect(rate).toHaveBeenLastCalledWith('s1', 'a9', false, undefined)
    await u.type(screen.getByLabelText('What was wrong? (optional)'), 'it was the capacitor')
    await u.click(within(screen.getByLabelText('What was wrong? (optional)').closest('form')!).getByRole('button', { name: 'Send' }))
    expect(rate).toHaveBeenLastCalledWith('s1', 'a9', false, 'it was the capacitor')
    expect(await screen.findByText('Thanks, noted')).toBeTruthy()
    await u.click(screen.getByRole('button', { name: 'Helpful' }))
    expect(rate).toHaveBeenLastCalledWith('s1', 'a9', true, undefined)
    expect(screen.getByRole('button', { name: 'Helpful' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('typed messages are answered in text only, even with the speaker on', async () => {
    const u = userEvent.setup()
    const speak = await chatPage()
    expect(screen.getByRole('button', { name: /Speaker on/ })).toBeTruthy()
    await type(u, 'Hi FixSaathi')
    await type(u, 'My fan hums but does not spin')
    expect(speak).not.toHaveBeenCalled()
  })

  it('a voice message is answered aloud with the natural voice when the speaker is on, and typing afterwards stays silent', async () => {
    const u = userEvent.setup()
    const speak = await chatPage()
    await say(u, 'fan is humming')
    await waitFor(() => expect(speak).toHaveBeenCalledTimes(1))
    const [text, opts] = speak.mock.calls[0]
    expect(text).toBe('Reply to fan is humming')
    expect(opts.source).toEqual({ sessionId: 's1', messageId: expect.stringMatching(/^a/) })
    expect(opts.aiVoice).toBe('personal')  // the technician's own ElevenLabs voice by default
    await type(u, 'and it is slow')
    expect(speak).toHaveBeenCalledTimes(1)  // switched to typing: no more automatic speech
  })

  it('a voice message gets text only when the speaker is off', async () => {
    store['fixsaathi.speaker'] = 'off'
    const u = userEvent.setup()
    const speak = await chatPage()
    expect(screen.getByRole('button', { name: /Speaker off/ })).toBeTruthy()
    await say(u, 'fan stopped')
    expect(speak).not.toHaveBeenCalled()
  })

  it('Read aloud speaks only the chosen reply, on request', async () => {
    store['fixsaathi.speaker'] = 'off'
    const u = userEvent.setup()
    const speak = await chatPage()
    await type(u, 'first question')
    await type(u, 'second question')
    expect(speak).not.toHaveBeenCalled()
    await u.click(screen.getAllByRole('button', { name: 'Read aloud' })[0])
    expect(speak).toHaveBeenCalledTimes(1)
    expect(speak.mock.calls[0][0]).toBe('Reply to first question')
  })
})

describe('speech output', () => {
  class FakeAudio {
    static last: FakeAudio | null = null
    src: string; playbackRate = 1; paused = true
    onended: (() => void) | null = null; onerror: (() => void) | null = null
    constructor(src: string) { this.src = src; FakeAudio.last = this }
    play() { this.paused = false; return Promise.resolve() }
    pause() { this.paused = true }
  }
  const device = () => {
    const said: string[] = []
    class U { text: string; voice = null; lang = ''; rate = 1; pitch = 1; volume = 1; onend: (() => void) | null = null; onerror = null; constructor(t: string) { this.text = t } }
    vi.stubGlobal('SpeechSynthesisUtterance', U)
    vi.stubGlobal('speechSynthesis', { getVoices: () => [], cancel: vi.fn(), speak: (u: U) => said.push(u.text) })
    return said
  }

  it('plays the natural voice from the server, and Speaker off stops it at once', async () => {
    const { speech } = await import('../services/speech')
    speech._reset(); device()
    vi.stubGlobal('Audio', FakeAudio)
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => undefined }))
    const fetchMock = vi.fn(async () => new Response(new Uint8Array([82, 73, 70, 70]), { status: 200, headers: { 'content-type': 'audio/wav' } }))
    vi.stubGlobal('fetch', fetchMock)
    speech.speak('Switch off the MCB first.', { language: 'English', aiVoice: 'Kore', source: { sessionId: 's1', messageId: 'a1' } })
    expect(speech.phase()).toBe('preparing')
    await waitFor(() => expect(speech.phase()).toBe('speaking'))
    expect(String((fetchMock.mock.calls[0] as unknown[])[0])).toMatch(/\/api\/v1\/sessions\/s1\/messages\/a1\/speech\?voice=Kore$/)
    expect(speech.engine()).toBe('natural')
    const audio = FakeAudio.last!
    expect(audio.paused).toBe(false)
    const u = userEvent.setup()
    localStorage.setItem('fixsaathi.speaker', 'on')  // an earlier test may have switched the speaker off on this device
    wrap(<Composer onSend={() => undefined} />)
    await u.click(screen.getByRole('button', { name: /Speaker on/ }))
    expect(audio.paused).toBe(true)
    expect(speech.phase()).toBe('idle')
  })

  it('plays the personal (ElevenLabs) voice when the server used it', async () => {
    const { speech } = await import('../services/speech')
    speech._reset(); device()
    vi.stubGlobal('Audio', FakeAudio)
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:y', revokeObjectURL: () => undefined }))
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new Uint8Array([73, 68, 51]), { status: 200, headers: { 'content-type': 'audio/mpeg', 'x-voice': 'personal' } })))
    speech.speak('Switch off the MCB first.', { language: 'English', aiVoice: 'personal', source: { sessionId: 's1', messageId: 'a9' } })
    await waitFor(() => expect(speech.phase()).toBe('speaking'))
    expect(speech.engine()).toBe('personal')
    expect(String((vi.mocked(fetch).mock.calls[0] as unknown[])[0])).toMatch(/speech\?voice=personal$/)
    speech.stop()
  })

  it('falls back to the device voice when the ElevenLabs key may not generate speech', async () => {
    const { speech } = await import('../services/speech')
    speech._reset(); const said = device()
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ error: { code: 'TTS_KEY_PERMISSION', message: 'not allowed' } }), { status: 503, headers: { 'content-type': 'application/json' } })))
    speech.speak('Check the regulator.', { language: 'English', aiVoice: 'personal', source: { sessionId: 's1', messageId: 'a1' } })
    await waitFor(() => expect(said).toEqual(['Check the regulator.']))
    expect(speech.engine()).toBe('device')
    speech.stop()
  })

  it('falls back to the device voice when the natural voice is out of quota, and stops asking for a while', async () => {
    const { speech } = await import('../services/speech')
    speech._reset(); const said = device()
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ error: { code: 'QUOTA_EXCEEDED', message: 'limit' } }), { status: 503, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    speech.speak('Check the regulator.', { language: 'English', aiVoice: 'Charon', source: { sessionId: 's1', messageId: 'a1' } })
    await waitFor(() => expect(said).toEqual(['Check the regulator.']))
    expect(speech.engine()).toBe('device')
    speech.speak('Spin the blades by hand.', { language: 'English', aiVoice: 'Charon', source: { sessionId: 's1', messageId: 'a2' } })
    expect(fetchMock).toHaveBeenCalledTimes(1)  // no second failing request
    expect(said).toEqual(['Check the regulator.', 'Spin the blades by hand.'])
    speech.stop()
  })

  it('a new reply stops the previous one: no overlapping playback', async () => {
    const { speech } = await import('../services/speech')
    speech._reset(); const said = device()
    speech.speak('First reply.', { language: 'English', aiVoice: 'device' })
    const cancel = (window.speechSynthesis.cancel as ReturnType<typeof vi.fn>)
    speech.speak('Second reply.', { language: 'English', aiVoice: 'device' })
    expect(cancel).toHaveBeenCalled()
    expect(said).toEqual(['First reply.', 'Second reply.'])
    speech.stop()
  })
})
