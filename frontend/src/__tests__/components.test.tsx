import { describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import LoginPage from '../pages/LoginPage'
import { Composer } from '../components/composer/Composer'
import { CameraModal } from '../components/camera/CameraModal'
import { AuthProvider } from '../context/AuthContext'
import { AppProvider, useApp } from '../context/AppContext'
import { PrefsProvider } from '../context/PrefsContext'
import * as services from '../services'
import { fileService } from '../services'
import { openFile } from '../utils/openFile'
import type { Attachment } from '../types'

const wrap = (ui: ReactNode) => render(<AuthProvider><PrefsProvider><AppProvider><MemoryRouter>{ui}</MemoryRouter></AppProvider></PrefsProvider></AuthProvider>)
const file = (name: string, type: string, size = 10) => new File([new Uint8Array(size)], name, { type })

// ---------------- password visibility ----------------

describe('password visibility', () => {
  it('toggles between hidden and visible, keeps the value and focus, and starts hidden', async () => {
    const u = userEvent.setup()
    wrap(<LoginPage />)
    const pw = screen.getByLabelText('Password') as HTMLInputElement
    expect(pw.type).toBe('password')
    await u.type(pw, 'secret pass 1')
    const toggle = screen.getByRole('button', { name: 'Show password' })
    expect(toggle.getAttribute('aria-pressed')).toBe('false')
    await u.click(toggle)
    expect(pw.type).toBe('text')
    expect(pw.value).toBe('secret pass 1')
    expect(screen.getByRole('button', { name: 'Hide password' }).getAttribute('aria-pressed')).toBe('true')
    await u.click(screen.getByRole('button', { name: 'Hide password' }))
    expect(pw.type).toBe('password')
  })

  it('works on registration too, with a live length hint, and resets when switching modes', async () => {
    const u = userEvent.setup()
    wrap(<LoginPage />)
    await u.click(screen.getByRole('button', { name: 'New here? Create an account' }))
    const pw = screen.getByLabelText('Password') as HTMLInputElement
    await u.type(pw, 'abc')
    expect(screen.getByText('5 more characters needed.')).toBeTruthy()
    await u.click(screen.getByRole('button', { name: 'Show password' }))
    expect(pw.type).toBe('text')
    await u.type(pw, 'defgh')
    expect(screen.getByText('Looks good.')).toBeTruthy()
    await u.click(screen.getByRole('button', { name: 'Already have an account? Sign in' }))
    expect((screen.getByLabelText('Password') as HTMLInputElement).type).toBe('password')
  })
})

// ---------------- attach menu and files ----------------

describe('attach menu', () => {
  it('opens from the plus button with three working options and closes with Escape', async () => {
    const u = userEvent.setup()
    wrap(<Composer onSend={() => undefined} />)
    const plus = screen.getByRole('button', { name: 'Add photos, documents or camera' })
    expect(plus.getAttribute('aria-expanded')).toBe('false')
    await u.click(plus)
    const menu = screen.getByRole('menu', { name: 'Attach' })
    const items = within(menu).getAllByRole('menuitem').map(b => b.textContent)
    expect(items.map(t => t?.split(/JPG|PDF,|Use/)[0])).toEqual(['Photos and images', 'PDF or document', 'Take a photo'])
    const clicked = vi.spyOn(HTMLInputElement.prototype, 'click')
    await u.click(within(menu).getByRole('menuitem', { name: /PDF or document/ }))
    expect(clicked).toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByRole('menu')).toBeNull())  // closes (after its short fade-out)
    await u.click(plus); await u.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('menu')).toBeNull())
  })

  it('attaches several images and documents, shows them, removes one, and sends them', async () => {
    const u = userEvent.setup()
    const sent: Attachment[][] = []
    wrap(<Composer onSend={(_t, a) => sent.push(a)} />)
    await u.upload(screen.getByTestId('attach-images'), [file('a.jpg', 'image/jpeg'), file('b.png', 'image/png')])
    await u.upload(screen.getByTestId('attach-docs'), [file('manual.pdf', 'application/pdf', 2048), file('notes.txt', 'text/plain'), file('sheet.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')])
    expect(screen.getByAltText('Attachment a.jpg')).toBeTruthy()
    expect(screen.getByText('manual.pdf')).toBeTruthy()
    expect(screen.getByText('PDF · 2 KB')).toBeTruthy()
    await u.click(screen.getByRole('button', { name: 'Remove notes.txt' }))
    expect(screen.queryByText('notes.txt')).toBeNull()
    await u.type(screen.getByLabelText('Describe the appliance issue'), 'see attached{Enter}')
    expect(sent[0].map(a => [a.name, a.kind])).toEqual([['a.jpg', 'image'], ['b.png', 'image'], ['manual.pdf', 'document'], ['sheet.docx', 'document']])
    expect(screen.queryByText('manual.pdf')).toBeNull()  // cleared after sending
  })

  it('refuses unsupported, oversized and too many files with clear messages', async () => {
    const u = userEvent.setup({ applyAccept: false })
    wrap(<Composer onSend={() => undefined} />)
    await u.upload(screen.getByTestId('attach-docs'), [file('virus.exe', 'application/x-msdownload'), file('big.pdf', 'application/pdf', 16 * 1024 * 1024)])
    const alert = screen.getByRole('alert')
    expect(alert.textContent).toMatch(/virus\.exe” is not a supported file/)
    expect(alert.textContent).toMatch(/big\.pdf” is larger than 15 MB/)
    await u.upload(screen.getByTestId('attach-images'), Array.from({ length: 7 }, (_, i) => file(`p${i}.jpg`, 'image/jpeg')))
    expect(screen.getAllByRole('listitem')).toHaveLength(6)
    expect(screen.getByRole('alert').textContent).toMatch(/up to 6 files/)
  })

  it('pastes an image from the clipboard', async () => {
    const u = userEvent.setup()
    wrap(<Composer onSend={() => undefined} />)
    await u.click(screen.getByLabelText('Describe the appliance issue'))
    await u.paste({ files: [file('screenshot.png', 'image/png')] } as unknown as DataTransfer)
    expect(screen.getByAltText('Attachment screenshot.png')).toBeTruthy()
  })
})

describe('file rules', () => {
  it('classifies by type and extension', () => {
    expect(fileService.check(file('a.webp', 'image/webp'))).toEqual({ kind: 'image' })
    expect(fileService.check(file('m.PDF', ''))).toEqual({ kind: 'document' })
    expect(fileService.check(file('r.csv', 'text/csv'))).toEqual({ kind: 'document' })
    expect('error' in fileService.check(file('x.gif', 'image/gif'))).toBe(true)
    expect('error' in fileService.check(file('e.txt', 'text/plain', 0))).toBe(true)
  })
})

// ---------------- a failed upload restores the draft ----------------

function Harness() {
  const { send, error } = useApp()
  return <><Composer onSend={(t, a) => void send(t, a)} />{error && <p data-testid="err">{error}</p>}</>
}

describe('send with attachments', () => {
  it('puts the text and files back in the box when an upload fails', async () => {
    const u = userEvent.setup()
    vi.spyOn(services.sessionService, 'create').mockResolvedValue({ id: 's1' } as never)
    vi.spyOn(services.fileService, 'upload').mockRejectedValue(Object.assign(new Error('That file type is not supported.'), { code: 'UNSUPPORTED_MEDIA_TYPE', status: 415 }))
    const chat = vi.spyOn(services.chatService, 'send')
    wrap(<Harness />)
    await u.upload(screen.getByTestId('attach-docs'), [file('manual.pdf', 'application/pdf')])
    await u.type(screen.getByLabelText('Describe the appliance issue'), 'check this{Enter}')
    await waitFor(() => expect(screen.getByTestId('err').textContent).toMatch(/Could not upload “manual\.pdf”.*back in the box/))
    expect((screen.getByLabelText('Describe the appliance issue') as HTMLTextAreaElement).value).toBe('check this')
    expect(screen.getByText('manual.pdf')).toBeTruthy()
    expect(chat).not.toHaveBeenCalled()
  })
})

// ---------------- camera ----------------

function mockCamera(result: 'ok' | string, devices = 2) {
  const track = { stop: vi.fn() }
  const stream = { getTracks: () => [track] } as unknown as MediaStream
  const getUserMedia = vi.fn(async (_c?: MediaStreamConstraints) => { void _c; if (result !== 'ok') throw new DOMException('x', result); return stream })
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia, enumerateDevices: async () => Array.from({ length: devices }, () => ({ kind: 'videoinput' })) } })
  return { getUserMedia, track }
}

describe('camera', () => {
  it('asks for the back camera, shows the live preview, switches camera, and releases it on close', async () => {
    const u = userEvent.setup()
    const { getUserMedia, track } = mockCamera('ok')
    const onClose = vi.fn()
    const { rerender } = render(<CameraModal open onClose={onClose} onUse={() => undefined} />)
    await screen.findByRole('button', { name: 'Capture photo' })
    expect(screen.getByLabelText('Live camera preview')).toBeTruthy()
    expect(getUserMedia.mock.calls[0][0]).toMatchObject({ video: { facingMode: { ideal: 'environment' } }, audio: false })
    await u.click(await screen.findByRole('button', { name: 'Switch to front camera' }))
    await waitFor(() => expect(getUserMedia.mock.calls.at(-1)?.[0]).toMatchObject({ video: { facingMode: { ideal: 'user' } } }))
    await u.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
    rerender(<CameraModal open={false} onClose={onClose} onUse={() => undefined} />)
    expect(track.stop).toHaveBeenCalled()
  })

  it.each([
    ['NotAllowedError', 'Camera permission was denied'],
    ['NotFoundError', 'No camera found'],
    ['NotReadableError', 'The camera is being used by another app'],
  ])('explains %s and offers the phone camera and gallery instead', async (err, text) => {
    mockCamera(err)
    render(<CameraModal open onClose={() => undefined} onUse={() => undefined} />)
    expect((await screen.findByRole('alert')).textContent).toContain(text)
    expect(screen.getByRole('button', { name: 'Use phone camera app' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Upload from gallery' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Try camera again' })).toBeTruthy()
  })

  it('needs https: explains instead of failing silently', async () => {
    mockCamera('ok')
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false })
    render(<CameraModal open onClose={() => undefined} onUse={() => undefined} />)
    expect((await screen.findByRole('alert')).textContent).toContain('Camera needs a secure connection')
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })
  })

  it('previews a photo, allows retake, and only hands it over after "Use this photo"', async () => {
    const u = userEvent.setup()
    mockCamera('NotAllowedError')
    const used: Attachment[] = []
    render(<CameraModal open onClose={() => undefined} onUse={a => used.push(a)} />)
    await screen.findByRole('alert')
    await u.upload(screen.getByTestId('camera-native'), file('IMG_1.jpg', 'image/jpeg', 500))
    expect(screen.getByAltText('Captured appliance preview')).toBeTruthy()
    expect(used).toHaveLength(0)
    await u.click(screen.getByRole('button', { name: 'Use this photo' }))
    expect(used[0]).toMatchObject({ name: 'IMG_1.jpg', kind: 'image', source: 'camera', size: 500 })
  })

  it('refuses a non-image picked as a photo', async () => {
    const u = userEvent.setup({ applyAccept: false })
    mockCamera('NotAllowedError')
    render(<CameraModal open onClose={() => undefined} onUse={() => undefined} />)
    await screen.findByRole('alert')
    await u.upload(screen.getByTestId('camera-gallery'), file('doc.pdf', 'application/pdf'))
    await waitFor(() => expect(screen.getAllByRole('alert').some(a => /not an image/.test(a.textContent || ''))).toBe(true))
  })
})

// ---------------- opening files ----------------

describe('openFile', () => {
  it('opens PDFs in a new tab and downloads Word files', async () => {
    const opened = vi.spyOn(window, 'open').mockReturnValue(null)
    const clicks = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    await act(() => openFile({ id: '1', url: 'blob:local/1', name: 'manual.pdf', kind: 'document' }))
    expect(opened).toHaveBeenCalledWith('blob:local/1', '_blank', 'noopener')
    await act(() => openFile({ id: '2', url: 'blob:local/2', name: 'sheet.docx', kind: 'document' }))
    expect(clicks).toHaveBeenCalled()
  })
})
