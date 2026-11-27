import fs from 'node:fs'
import path from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import EvaluationPage from '../pages/EvaluationPage'
import { ApiError } from '../services/api'
import * as services from '../services'
import type { EvaluationResults } from '../services'

const REAL_RESULTS = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../../docs/EVALUATION_RESULTS.json'), 'utf-8'),
) as EvaluationResults

describe('EvaluationPage', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('renders exact held-out retrieval and safety numbers from docs/EVALUATION_RESULTS.json', async () => {
    const u = userEvent.setup()
    vi.spyOn(services.systemService, 'evaluation').mockResolvedValue(REAL_RESULTS)
    render(<MemoryRouter><EvaluationPage /></MemoryRouter>)

    expect(await screen.findByText('Retrieval & Safety Evaluation')).toBeTruthy()
    expect(screen.getByText('12/12')).toBeTruthy()
    expect(screen.getByText('11/12')).toBeTruthy()
    expect(screen.getByText(/hs08/)).toBeTruthy()
    expect(screen.getAllByText('94.4%').length).toBeGreaterThan(0)
    expect(screen.getAllByText('raw 0.944').length).toBeGreaterThan(0)
    expect(screen.getByText('0.958')).toBeTruthy()
    expect(screen.getAllByText(/v2-26/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/v2-29/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/v2-07/).length).toBeGreaterThan(0)
    expect(screen.getByText(/h28/)).toBeTruthy()

    await u.click(screen.getByRole('button', { name: 'Auto-detected' }))
    expect(screen.getAllByText('94.4%').length).toBeGreaterThan(0)
  })

  it('shows retry error state when evaluation fetch fails', async () => {
    const u = userEvent.setup()
    const spy = vi.spyOn(services.systemService, 'evaluation')
      .mockRejectedValueOnce(new ApiError(503, 'SERVER_WAKING', 'Could not load evaluation results.'))
      .mockResolvedValueOnce(REAL_RESULTS)

    render(<MemoryRouter><EvaluationPage /></MemoryRouter>)
    expect((await screen.findByRole('alert')).textContent).toContain('Could not load')
    await u.click(screen.getByRole('button', { name: 'Try again' }))
    expect(spy).toHaveBeenCalledTimes(2)
    expect(await screen.findByText('12/12')).toBeTruthy()
  })
})
