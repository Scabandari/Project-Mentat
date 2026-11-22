import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { FlipProblem, NextOut } from '@/api'
import { makeStore } from '@/app/store'
import { mockApi } from '@/test/mockApi'

import { StudyPage } from './StudyPage'

const SID = 'sess-1'

function flip(n: number): FlipProblem {
  return {
    answer_type: 'flip',
    instance_id: `inst-${n}`,
    card_id: `card-${n}`,
    deck_slug: 'number-fluency',
    prompt: `Question ${n}`,
    back_md: `**Answer ${n}**`,
    target_ms: 5000,
    is_new: true,
  }
}

function renderStudy() {
  const router = createMemoryRouter(
    [
      { path: '/study/:sessionId', element: <StudyPage /> },
      { path: '/', element: <div>home</div> },
    ],
    { initialEntries: [`/study/${SID}`] },
  )
  return render(
    <Provider store={makeStore()}>
      <RouterProvider router={router} />
    </Provider>,
  )
}

describe('StudyPage', () => {
  it('reveals, rates, advances, and shows the summary when the queue empties', async () => {
    const queue: NextOut[] = [
      { problem: flip(1), queue: { due: 0, new: 2, reviewed: 0 } },
      { problem: flip(2), queue: { due: 0, new: 1, reviewed: 1 } },
      { problem: null, queue: { due: 0, new: 0, reviewed: 2 } },
    ]
    let served = 0
    const { calls } = mockApi({
      'GET /api/v1/me/settings': {
        stakes_format: 'online',
        daily_new_limit: 10,
        show_timer: false,
      },
      [`POST /api/v1/sessions/${SID}/next`]: () => {
        // `next` is idempotent until answered: only advance after an answer was posted.
        const answered = calls.filter((c) => c.key.endsWith('/answer')).length
        served = Math.min(answered, queue.length - 1)
        return queue[served]
      },
      'POST /api/v1/instances/inst-1/answer': { rating: 'good' },
      'POST /api/v1/instances/inst-2/answer': { rating: 'again' },
      [`POST /api/v1/sessions/${SID}/end`]: {
        session_id: SID,
        mode: 'review',
        reviewed: 2,
        correct: 1,
        accuracy: 0.5,
        median_latency_ms: 2400,
        duration_s: 42,
        by_deck: [],
      },
    })
    const user = userEvent.setup()
    renderStudy()

    expect(await screen.findByText('Question 1')).toBeInTheDocument()
    expect(screen.queryByText('Answer 1')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Show answer' }))
    expect(screen.getByText('Answer 1')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Good/ }))

    expect(await screen.findByText('Question 2')).toBeInTheDocument()
    await user.keyboard(' ')
    expect(screen.getByText('Answer 2')).toBeInTheDocument()
    await user.keyboard('1')

    expect(await screen.findByText('Session complete')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()

    const answers = calls.filter((c) => c.key.endsWith('/answer'))
    expect(answers.map((a) => (a.body as { self_rating: string }).self_rating)).toEqual([
      'good',
      'again',
    ])
    expect(
      answers.every((a) => typeof (a.body as { latency_ms: number }).latency_ms === 'number'),
    ).toBe(true)
  })
})
