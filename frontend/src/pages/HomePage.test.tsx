import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'

import type { PackDetailOut } from '@/api'
import { mockApi } from '@/test/mockApi'
import { renderWithStore } from '@/test/renderWithStore'

import { HomePage } from './HomePage'

const pack: PackDetailOut = {
  id: 'p1',
  slug: 'poker-math',
  name: 'Poker Math',
  description: '',
  deck_count: 2,
  due_count: 3,
  new_count: 10,
  new_today: 10,
  decks: [
    {
      id: 'd1',
      slug: 'number-fluency',
      name: 'Number Fluency',
      description: '',
      section: 1,
      card_count: 21,
      due_count: 3,
      new_count: 10,
      mastery: 0.2,
      locked: false,
      has_lesson: false,
    },
    {
      id: 'd2',
      slug: 'mixed-spots',
      name: 'Mixed Spots',
      description: '',
      section: 11,
      card_count: 0,
      due_count: 0,
      new_count: 0,
      mastery: 0,
      locked: true,
      has_lesson: false,
    },
  ],
}

describe('HomePage', () => {
  it('shows counts, decks and toggles the stakes format', async () => {
    let format = 'online'
    const { calls } = mockApi({
      'GET /api/v1/packs/poker-math': pack,
      'GET /api/v1/me/settings': () => ({ stakes_format: format }),
      'PATCH /api/v1/me/settings': (body: unknown) => {
        format = (body as { stakes_format: string }).stakes_format
        return { stakes_format: format }
      },
    })
    const user = userEvent.setup()
    renderWithStore(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Number Fluency')).toBeInTheDocument()
    expect(screen.getByText('3 due · 10 new')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Study Mixed Spots' })).toBeDisabled()

    const live = screen.getByRole('radio', { name: 'Live' })
    await waitFor(() => expect(live).toBeEnabled())
    await user.click(live)
    await waitFor(() => expect(live).toHaveAttribute('aria-checked', 'true'))
    expect(calls.find((c) => c.key === 'PATCH /api/v1/me/settings')?.body).toEqual({
      stakes_format: 'live',
    })
  })
})
