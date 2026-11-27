import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { AppProvider, useApp } from '../context/AppContext'
import { PrefsProvider } from '../context/PrefsContext'
import { ChatThread } from '../components/chat/ChatThread'
import * as services from '../services'
import { StreamFallbackError } from '../services'

function Harness() {
  const { send } = useApp()
  return (
    <>
      <button type="button" onClick={() => void send('fan hums')}>Send</button>
      <ChatThread />
    </>
  )
}

const wrap = () => render(
  <AuthProvider><PrefsProvider><AppProvider><MemoryRouter><Harness /></MemoryRouter></AppProvider></PrefsProvider></AuthProvider>,
)

describe('SSE streaming and non-streaming fallback', () => {
  beforeEach(() => { Element.prototype.scrollIntoView = () => undefined })
  afterEach(() => { vi.restoreAllMocks() })

  it('streams SSE deltas incrementally and replaces with final server message', async () => {
    vi.spyOn(services.sessionService, 'create').mockResolvedValue({ id: 's1', title: 'Fan' } as never)
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({ id: 's1', title: 'Fan' } as never)
    const fallbackSend = vi.spyOn(services.chatService, 'send')
    vi.spyOn(services.chatService, 'stream').mockImplementation(async (_sid, _text, _media, _ch, cb) => {
      const now = new Date().toISOString()
      cb.onUserMessage?.({ id: 'u1', role: 'user', message: 'fan hums', message_type: 'text', meta: {}, created_at: now })
      cb.onDelta?.('Checking capacitor. ')
      cb.onDelta?.('Replace only after isolation.')
      cb.onDone?.({ id: 'a1', role: 'assistant', message: 'Checking capacitor. Replace only after isolation.', message_type: 'text', meta: { ai_generated: true }, created_at: now })
    })

    wrap()
    await act(async () => { screen.getByRole('button', { name: 'Send' }).click() })

    expect(await screen.findByText('Checking capacitor. Replace only after isolation.')).toBeTruthy()
    expect(fallbackSend).not.toHaveBeenCalled()
  })

  it('automatically falls back to non-streaming POST /messages when streaming fails', async () => {
    vi.spyOn(services.sessionService, 'create').mockResolvedValue({ id: 's1', title: 'Fan' } as never)
    vi.spyOn(services.sessionService, 'get').mockResolvedValue({ id: 's1', title: 'Fan' } as never)
    vi.spyOn(services.chatService, 'stream').mockRejectedValue(new StreamFallbackError('Stream blocked'))
    const now = new Date().toISOString()
    const sendSpy = vi.spyOn(services.chatService, 'send').mockResolvedValue({
      user_message: { id: 'u1', role: 'user', message: 'fan hums', message_type: 'text', meta: {}, created_at: now },
      assistant_message: { id: 'a1', role: 'assistant', message: 'Fallback reply from server.', message_type: 'text', meta: { ai_generated: true }, created_at: now },
      ai_status: 'ok',
      ai_error: null,
    })

    wrap()
    await act(async () => { screen.getByRole('button', { name: 'Send' }).click() })

    expect(await screen.findByText('Fallback reply from server.')).toBeTruthy()
    expect(sendSpy).toHaveBeenCalledTimes(1)
  })
})
