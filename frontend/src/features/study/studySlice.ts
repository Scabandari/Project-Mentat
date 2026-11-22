import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

import type { GradeOut } from '@/api'
import type { RootState } from '@/app/store'

import type { Response } from './AnswerInputs'

export type StudyPhase = 'loading' | 'question' | 'revealed' | 'grading' | 'graded' | 'done'

export interface StudyState {
  sessionId: string | null
  instanceId: string | null
  phase: StudyPhase
  shownAt: number | null
  revealedAt: number | null // flip: answer revealed
  answeredAt: number | null // auto-graded: option picked
  selected: Response | null
  lastGrade: GradeOut | null
}

const initialState: StudyState = {
  sessionId: null,
  instanceId: null,
  phase: 'loading',
  shownAt: null,
  revealedAt: null,
  answeredAt: null,
  selected: null,
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
      state.answeredAt = null
      state.selected = null
      state.lastGrade = null
    },
    answerRevealed(state, action: PayloadAction<{ at: number }>) {
      if (state.phase !== 'question') return
      state.phase = 'revealed'
      state.revealedAt = action.payload.at
    },
    answerSelected(state, action: PayloadAction<{ response: Response; at: number }>) {
      if (state.phase !== 'question') return
      state.phase = 'grading'
      state.selected = action.payload.response
      state.answeredAt = action.payload.at
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
  answerSelected,
  gradingStarted,
  gradeReceived,
  nextRequested,
  queueEmptied,
} = studySlice.actions

const elapsed = (from: number | null, to: number | null) =>
  from !== null && to !== null ? Math.max(0, Math.round(to - from)) : 0

/** Recall latency for flip cards: time from showing the card to revealing the answer. */
export const selectFlipLatency = (s: RootState): number =>
  elapsed(s.study.shownAt, s.study.revealedAt)

/** Answer latency for auto-graded cards: time from showing the card to picking an option. */
export const selectAnswerLatency = (s: RootState): number =>
  elapsed(s.study.shownAt, s.study.answeredAt)

export default studySlice.reducer
