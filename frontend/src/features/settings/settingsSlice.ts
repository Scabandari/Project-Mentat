import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export interface SettingsState {
  dailyNewLimit: number
  showTimer: boolean
}

const initialState: SettingsState = {
  dailyNewLimit: 10,
  showTimer: true,
}

export const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    setDailyNewLimit(state, action: PayloadAction<number>) {
      state.dailyNewLimit = Math.max(0, Math.min(100, Math.round(action.payload)))
    },
    toggleTimer(state) {
      state.showTimer = !state.showTimer
    },
  },
})

export const { setDailyNewLimit, toggleTimer } = settingsSlice.actions
export default settingsSlice.reducer
