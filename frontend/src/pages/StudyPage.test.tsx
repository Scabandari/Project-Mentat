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

describe('StudyPage, generated cards', () => {
  it('answers a bucket card, shows the result, then continues', async () => {
    const bucket: NextOut = {
      problem: {
        answer_type: 'bucket',
        instance_id: 'inst-b',
        card_id: 'card-b',
        deck_slug: 'pot-odds',
        prompt: 'Pot is **$100**. Villain bets $50. Equity needed?',
        scene: {
          pot: 100,
          bet: 50,
          money_format: 'live',
          hero: ['Ah', 'Kh'],
          board: ['Qh', '7h', '2c'],
        },
        target_ms: 10000,
        is_new: false,
        unit: 'percent',
        buckets: [
          { id: 0, label: '10–20%', lo: 10, hi: 20 },
          { id: 1, label: '20–30%', lo: 20, hi: 30 },
          { id: 2, label: '30–40%', lo: 30, hi: 40 },
          { id: 3, label: '40–50%', lo: 40, hi: 50 },
          { id: 4, label: '50–60%', lo: 50, hi: 60 },
        ],
      },
      queue: { due: 1, new: 0, reviewed: 0 },
    }
    let answered = false
    const { calls } = mockApi({
      'GET /api/v1/me/settings': { show_timer: false },
      'GET /api/v1/config': { tutor_enabled: false },
      [`POST /api/v1/sessions/${SID}/next`]: () =>
        answered ? { problem: null, queue: { due: 0, new: 0, reviewed: 1 } } : bucket,
      'POST /api/v1/instances/inst-b/answer': () => {
        answered = true
        return {
          instance_id: 'inst-b',
          is_correct: false,
          rating: 'again',
          correct_response: 1,
          exact_answer: 25,
          back_md: null,
          shortcut: 'Call ÷ final pot.',
          explanation_md: '$50 ÷ $200 = **25%**',
          latency_ms: 4200,
          target_ms: 10000,
          next_due: null,
        }
      },
      [`POST /api/v1/sessions/${SID}/end`]: {
        session_id: SID,
        mode: 'review',
        reviewed: 1,
        correct: 0,
        accuracy: 0,
        median_latency_ms: 4200,
        duration_s: 9,
        by_deck: [],
      },
    })
    const user = userEvent.setup()
    renderStudy()

    expect(await screen.findByText(/Equity needed/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'A of hearts' })).toBeInTheDocument()
    expect(screen.getByText('Pot $100')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /30–40%/ }))
    expect(await screen.findByText('Not quite')).toBeInTheDocument()
    expect(screen.getByText('25%', { selector: 'span' })).toBeInTheDocument() // exact, with unit
    expect(screen.getByText(/Call ÷ final pot/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /30–40%/ })).toHaveAttribute('aria-pressed', 'true')

    const answer = calls.find((c) => c.key.endsWith('/answer'))!.body as Record<string, unknown>
    expect(answer.response).toBe(2)
    expect(typeof answer.latency_ms).toBe('number')

    await user.click(screen.getByRole('button', { name: 'Continue' }))
    expect(await screen.findByText('Session complete')).toBeInTheDocument()
  })
})
