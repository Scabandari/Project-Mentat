// App-facing API: generated endpoints plus cache-invalidation rules codegen can't infer.
// Import hooks from here, not from ./generated.
import { mentatApi } from './generated'

export const api = mentatApi.enhanceEndpoints({
  endpoints: {
    answerProblem: { invalidatesTags: ['study', 'catalog'] },
    endSession: { invalidatesTags: ['study', 'catalog'] },
    updateSettings: { invalidatesTags: ['me'] },
  },
})

export * from './generated'
