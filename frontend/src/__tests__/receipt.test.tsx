import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ReceiptPage from '../pages/ReceiptPage'
import * as services from '../services'

describe('Customer Safety Receipt page (/receipt/:id)', () => {
  afterEach(() => { vi.restoreAllMocks() })
  beforeEach(() => { Element.prototype.scrollIntoView = () => undefined })

  it('defaults to Hindi, toggles cleanly to English, and renders scannable QR img', async () => {
    vi.spyOn(services.receiptService, 'getPublic').mockResolvedValue({
      token: 'tok-abc123456789012345',
      created_at: '2026-11-28T06:00:00Z',
      expires_at: '2026-12-28T06:00:00Z',
      qr_url: '/api/v1/receipts/tok-abc123456789012345/qr',
      receipt: {
        session_reference: 'FS-77',
        appliance_type: 'split_ac',
        appliance_en: 'Split AC',
        appliance_hi: 'स्प्लिट एसी',
        unit_label: 'LG LS-Q18YNZA',
        issue: 'CH38 cooling issue',
        checks_done: ['Cleaned indoor air filter'],
        parts: ['Outdoor unit'],
        safety_status: {
          power_off_confirmed: true,
          tester_checked: true,
          unlocked: true,
          blocked_attempts: 1,
          disclaimer_en: 'Technician statement only.',
          disclaimer_hi: 'यह विवरण टेक्नीशियन द्वारा दर्ज जानकारी पर आधारित है।',
        },
        technician_name: 'Ramesh Kumar',
        issued_at: '2026-11-28T06:00:00Z',
      },
    })

    render(
      <MemoryRouter initialEntries={['/receipt/tok-abc123456789012345']}>
        <Routes><Route path="/receipt/:id" element={<ReceiptPage />} /></Routes>
      </MemoryRouter>,
    )

    // Hindi first
    expect(await screen.findByText('ग्राहक सुरक्षा रसीद')).toBeTruthy()
    expect(screen.getByText('स्प्लिट एसी')).toBeTruthy()
    expect(screen.getByText('Ramesh Kumar')).toBeTruthy()
    expect(screen.getByAltText('सुरक्षा रसीद का QR कोड')).toBeTruthy()

    // Switch to English
    fireEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByText('Customer Safety Receipt')).toBeTruthy()
    expect(screen.getByText('Split AC')).toBeTruthy()
    expect(screen.getByAltText('Safety receipt QR code')).toBeTruthy()
  })

  it('shows expired notice cleanly when receipt has expired', async () => {
    vi.spyOn(services.receiptService, 'getPublic').mockRejectedValue(new Error('This safety receipt has expired.'))

    render(
      <MemoryRouter initialEntries={['/receipt/expired-tok-123456']}>
        <Routes><Route path="/receipt/:id" element={<ReceiptPage />} /></Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('यह सुरक्षा रसीद समाप्त हो चुकी है')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByText('This safety receipt has expired')).toBeTruthy()
  })
})
