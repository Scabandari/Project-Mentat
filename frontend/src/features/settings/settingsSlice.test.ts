import reducer, { setDailyNewLimit, toggleTimer } from './settingsSlice'

describe('settingsSlice', () => {
  it('clamps the daily new-card limit', () => {
    const state = reducer(undefined, setDailyNewLimit(500))
    expect(state.dailyNewLimit).toBe(100)
    expect(reducer(state, setDailyNewLimit(-3)).dailyNewLimit).toBe(0)
  })

  it('toggles the timer', () => {
    expect(reducer(undefined, toggleTimer()).showTimer).toBe(false)
  })
})
