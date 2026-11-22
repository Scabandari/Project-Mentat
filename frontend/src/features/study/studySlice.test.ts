import { makeStore } from '@/app/store'

import {
  answerRevealed,
  gradingStarted,
  problemShown,
  queueEmptied,
  selectFlipLatency,
  sessionStarted,
} from './studySlice'

describe('studySlice', () => {
  it('measures recall latency from show to reveal', () => {
    const store = makeStore()
    store.dispatch(sessionStarted('s1'))
    store.dispatch(problemShown({ instanceId: 'i1', at: 1_000 }))
    expect(store.getState().study.phase).toBe('question')
    store.dispatch(answerRevealed({ at: 4_250 }))
    expect(store.getState().study.phase).toBe('revealed')
    expect(selectFlipLatency(store.getState())).toBe(3_250)
  })

  it('ignores a repeated problemShown for the same instance (StrictMode / idempotent next)', () => {
    const store = makeStore()
    store.dispatch(problemShown({ instanceId: 'i1', at: 1_000 }))
    store.dispatch(problemShown({ instanceId: 'i1', at: 9_000 }))
    expect(store.getState().study.shownAt).toBe(1_000)
  })

  it('only reveals from the question phase', () => {
    const store = makeStore()
    store.dispatch(problemShown({ instanceId: 'i1', at: 0 }))
    store.dispatch(answerRevealed({ at: 10 }))
    store.dispatch(gradingStarted())
    store.dispatch(answerRevealed({ at: 99 }))
    expect(store.getState().study.revealedAt).toBe(10)
  })

  it('marks the session done when the queue empties', () => {
    const store = makeStore()
    store.dispatch(problemShown({ instanceId: 'i1', at: 0 }))
    store.dispatch(queueEmptied())
    expect(store.getState().study).toMatchObject({ phase: 'done', instanceId: null })
  })
})
