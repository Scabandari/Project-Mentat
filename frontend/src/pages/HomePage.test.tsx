import { screen } from '@testing-library/react'
import { vi } from 'vitest'

import { renderWithStore } from '@/test/renderWithStore'

import { HomePage } from './HomePage'

function mockFetch(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('HomePage', () => {
  it('shows healthy API status', async () => {
    mockFetch({ status: 'ok', db: 'ok', version: '0.1.0' })
    renderWithStore(<HomePage />)
    expect(await screen.findByText('API ok · DB ok · v0.1.0')).toBeInTheDocument()
  })

  it('shows unreachable when the API errors', async () => {
    mockFetch({ error: { code: 'http_500', message: 'boom' } }, 500)
    renderWithStore(<HomePage />)
    expect(await screen.findByText('API unreachable')).toBeInTheDocument()
  })
})
