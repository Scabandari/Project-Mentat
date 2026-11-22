import { screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import type { StatsOverviewOut } from '@/api'
import { mockApi } from '@/test/mockApi'
import { renderWithStore } from '@/test/renderWithStore'

import { StatsPage } from './StatsPage'

const days = Array.from({ length: 14 }, (_, i) => ({
  date: `2026-11-${String(8 + i).padStart(2, '0')}`,
  reviews: i % 3,
  correct: i % 2,
}))

const deck = {
  deck_id: 'd3',
  deck_name: 'Outs & Draws',
  section: 3,
  reviews: 12,
  accuracy: 0.5,
  median_latency_ms: 8400,
  on_time: 0.25,
  mastery: 0.1,
}

const overview: StatsOverviewOut = {
  streak_days: 4,
  reviews_today: 17,
  due_now: 6,
  reviews_7d: 80,
  accuracy_7d: 0.812,
  median_latency_ms_7d: 6200,
  daily: days,
  decks: [deck],
  weakest: [deck],
}

describe('StatsPage', () => {
  it('shows headline numbers, weakest decks and per-section rows', async () => {
    mockApi({ 'GET /api/v1/stats/overview': overview })
    renderWithStore(
      <MemoryRouter>
        <StatsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('81%')).toBeInTheDocument()
    expect(screen.getByText('6.2s')).toBeInTheDocument()
    expect(screen.getByText('17')).toBeInTheDocument()
    expect(screen.getByText('50% right · 25% on time')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Drill/ })).toBeEnabled()
    expect(screen.getByRole('img', { name: 'Reviews per day' })).toBeInTheDocument()
  })
})
