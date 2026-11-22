import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

import type { GradeOut } from '@/api'
import type { RootState } from '@/app/store'

export type StudyPhase = 'loading' | 'question' | 'revealed' | 'grading' | 'graded' | 'done'

export interface StudyState {
  sessionId: string | null
  instanceId: string | null
  phase: StudyPhase
  shownAt: number | null
  revealedAt: number | null
  lastGrade: GradeOut | null
}

const initialState: StudyState = {
  sessionId: null,
  instanceId: null,
  phase: 'loading',
  shownAt: null,
  revealedAt: null,
  lastGrade: null,
}

export const studySlice = createSlice({
  name: 'study',
  initialState,
  reducers: {
    sessionStarted(_state, action: PayloadAction<string>) {
      return { ...initialState, sessionId: action.payload }
    },
    problemShown(state, action: PayloadAction<{ instanceId: string; at: number }>) {
      if (state.instanceId === action.payload.instanceId && state.phase !== 'loading') return
      state.instanceId = action.payload.instanceId
      state.phase = 'question'
      state.shownAt = action.payload.at
      state.revealedAt = null
      state.lastGrade = null
    },
    answerRevealed(state, action: PayloadAction<{ at: number }>) {
      if (state.phase !== 'question') return
      state.phase = 'revealed'
      state.revealedAt = action.payload.at
    },
    gradingStarted(state) {
      state.phase = 'grading'
    },
    gradeReceived(state, action: PayloadAction<GradeOut>) {
      state.phase = 'graded'
      state.lastGrade = action.payload
    },
    nextRequested(state) {
      state.phase = 'loading'
    },
    queueEmptied(state) {
      state.phase = 'done'
      state.instanceId = null
    },
  },
})

export const {
  sessionStarted,
  problemShown,
  answerRevealed,
  gradingStarted,
  gradeReceived,
  nextRequested,
  queueEmptied,
} = studySlice.actions

/** Recall latency for flip cards: time from showing the card to revealing the answer. */
export const selectFlipLatency = (s: RootState): number =>
  s.study.shownAt !== null && s.study.revealedAt !== null
    ? Math.max(0, Math.round(s.study.revealedAt - s.study.shownAt))
    : 0

export default studySlice.reducer
