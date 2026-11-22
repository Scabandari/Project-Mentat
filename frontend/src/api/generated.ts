import { baseApi as api } from './baseApi'
export const addTagTypes = ['health', 'me', 'catalog', 'study', 'meta', 'stats'] as const
const injectedRtkApi = api
  .enhanceEndpoints({
    addTagTypes,
  })
  .injectEndpoints({
    endpoints: (build) => ({
      getHealth: build.query<GetHealthApiResponse, GetHealthApiArg>({
        query: () => ({ url: `/api/v1/health` }),
        providesTags: ['health'],
      }),
      getSettings: build.query<GetSettingsApiResponse, GetSettingsApiArg>({
        query: () => ({ url: `/api/v1/me/settings` }),
        providesTags: ['me'],
      }),
      updateSettings: build.mutation<UpdateSettingsApiResponse, UpdateSettingsApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/me/settings`,
          method: 'PATCH',
          body: queryArg.settingsIn,
        }),
        invalidatesTags: ['me'],
      }),
      listPacks: build.query<ListPacksApiResponse, ListPacksApiArg>({
        query: () => ({ url: `/api/v1/packs` }),
        providesTags: ['catalog'],
      }),
      getPack: build.query<GetPackApiResponse, GetPackApiArg>({
        query: (queryArg) => ({ url: `/api/v1/packs/${queryArg.slug}` }),
        providesTags: ['catalog'],
      }),
      getDeck: build.query<GetDeckApiResponse, GetDeckApiArg>({
        query: (queryArg) => ({ url: `/api/v1/decks/${queryArg.deckId}` }),
        providesTags: ['catalog'],
      }),
      createSession: build.mutation<CreateSessionApiResponse, CreateSessionApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/sessions`,
          method: 'POST',
          body: queryArg.sessionIn,
        }),
        invalidatesTags: ['study'],
      }),
      nextProblem: build.mutation<NextProblemApiResponse, NextProblemApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/sessions/${queryArg.sessionId}/next`,
          method: 'POST',
        }),
        invalidatesTags: ['study'],
      }),
      endSession: build.mutation<EndSessionApiResponse, EndSessionApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/sessions/${queryArg.sessionId}/end`,
          method: 'POST',
        }),
        invalidatesTags: ['study'],
      }),
      answerProblem: build.mutation<AnswerProblemApiResponse, AnswerProblemApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/instances/${queryArg.instanceId}/answer`,
          method: 'POST',
          body: queryArg.answerIn,
        }),
        invalidatesTags: ['study'],
      }),
      tutorExplain: build.mutation<TutorExplainApiResponse, TutorExplainApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/instances/${queryArg.instanceId}/tutor`,
          method: 'POST',
          body: queryArg.tutorIn,
        }),
        invalidatesTags: ['study'],
      }),
      getConfig: build.query<GetConfigApiResponse, GetConfigApiArg>({
        query: () => ({ url: `/api/v1/config` }),
        providesTags: ['study', 'meta'],
      }),
      getStatsOverview: build.query<GetStatsOverviewApiResponse, GetStatsOverviewApiArg>({
        query: () => ({ url: `/api/v1/stats/overview` }),
        providesTags: ['stats'],
      }),
      getDeckStats: build.query<GetDeckStatsApiResponse, GetDeckStatsApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/stats/decks/${queryArg.deckId}`,
        }),
        providesTags: ['stats'],
      }),
    }),
    overrideExisting: false,
  })
export { injectedRtkApi as mentatApi }
export type GetHealthApiResponse = /** status 200 Successful Response */ HealthOut
export type GetHealthApiArg = void
export type GetSettingsApiResponse = /** status 200 Successful Response */ SettingsOut
export type GetSettingsApiArg = void
export type UpdateSettingsApiResponse = /** status 200 Successful Response */ SettingsOut
export type UpdateSettingsApiArg = {
  settingsIn: SettingsIn
}
export type ListPacksApiResponse = /** status 200 Successful Response */ PackOut[]
export type ListPacksApiArg = void
export type GetPackApiResponse = /** status 200 Successful Response */ PackDetailOut
export type GetPackApiArg = {
  slug: string
}
export type GetDeckApiResponse = /** status 200 Successful Response */ DeckDetailOut
export type GetDeckApiArg = {
  deckId: string
}
export type CreateSessionApiResponse = /** status 201 Successful Response */ SessionOut
export type CreateSessionApiArg = {
  sessionIn: SessionIn
}
export type NextProblemApiResponse = /** status 200 Successful Response */ NextOut
export type NextProblemApiArg = {
  sessionId: string
}
export type EndSessionApiResponse = /** status 200 Successful Response */ SessionSummaryOut
export type EndSessionApiArg = {
  sessionId: string
}
export type AnswerProblemApiResponse = /** status 200 Successful Response */ GradeOut
export type AnswerProblemApiArg = {
  instanceId: string
  answerIn: AnswerIn
}
export type TutorExplainApiResponse = /** status 200 Successful Response */ TutorOut
export type TutorExplainApiArg = {
  instanceId: string
  tutorIn: TutorIn
}
export type GetConfigApiResponse = /** status 200 Successful Response */ ConfigOut
export type GetConfigApiArg = void
export type GetStatsOverviewApiResponse = /** status 200 Successful Response */ StatsOverviewOut
export type GetStatsOverviewApiArg = void
export type GetDeckStatsApiResponse = /** status 200 Successful Response */ DeckStatsOut
export type GetDeckStatsApiArg = {
  deckId: string
}
export type HealthOut = {
  status: 'ok' | 'degraded'
  db: 'ok' | 'down'
  version: string
}
export type SettingsOut = {
  stakes_format?: 'live' | 'online'
  daily_new_limit?: number
  show_timer?: boolean
  timezone?: string
}
export type ValidationError = {
  loc: (string | number)[]
  msg: string
  type: string
  input?: any
  ctx?: object
}
export type HttpValidationError = {
  detail?: ValidationError[]
}
export type SettingsIn = {
  stakes_format?: ('live' | 'online') | null
  daily_new_limit?: number | null
  show_timer?: boolean | null
  timezone?: string | null
}
export type PackOut = {
  id: string
  slug: string
  name: string
  description: string
  deck_count: number
  due_count: number
  new_count: number
  new_today: number
}
export type DeckOut = {
  id: string
  slug: string
  name: string
  description: string
  section: number
  card_count: number
  due_count: number
  new_count: number
  mastery: number
  locked: boolean
  has_lesson: boolean
}
export type PackDetailOut = {
  id: string
  slug: string
  name: string
  description: string
  deck_count: number
  due_count: number
  new_count: number
  new_today: number
  decks: DeckOut[]
}
export type DeckDetailOut = {
  id: string
  slug: string
  name: string
  description: string
  section: number
  card_count: number
  due_count: number
  new_count: number
  mastery: number
  locked: boolean
  has_lesson: boolean
  lesson_md: string | null
}
export type SessionOut = {
  id: string
  mode: 'review' | 'drill' | 'learn'
  deck_ids: string[]
  started_at: string
  due_count: number
  new_count: number
}
export type ErrorBody = {
  code: string
  message: string
  details?: any | null
}
export type ErrorOut = {
  error: ErrorBody
}
export type SessionIn = {
  mode?: 'review' | 'drill' | 'learn'
  deck_ids?: string[] | null
  new_limit?: number | null
}
export type Scene = {
  hero?: string[]
  villain?: string[]
  board?: string[]
  pot?: number | null
  bet?: number | null
  hero_stack?: number | null
  villain_stack?: number | null
  street?: ('preflop' | 'flop' | 'turn' | 'river') | null
  money_format?: ('live' | 'online') | null
}
export type ActionProblem = {
  instance_id: string
  card_id: string
  deck_slug: string
  prompt: string
  scene?: Scene | null
  target_ms: number
  is_new: boolean
  answer_type: 'action'
  actions: ('fold' | 'call' | 'raise')[]
}
export type Bucket = {
  id: number
  label: string
  lo: number
  hi: number
}
export type BucketProblem = {
  instance_id: string
  card_id: string
  deck_slug: string
  prompt: string
  scene?: Scene | null
  target_ms: number
  is_new: boolean
  answer_type: 'bucket'
  unit: 'percent' | 'count' | 'ratio' | 'chips'
  buckets: Bucket[]
}
export type Choice = {
  id: number
  label: string
}
export type ChoiceProblem = {
  instance_id: string
  card_id: string
  deck_slug: string
  prompt: string
  scene?: Scene | null
  target_ms: number
  is_new: boolean
  answer_type: 'choice'
  choices: Choice[]
}
export type FlipProblem = {
  instance_id: string
  card_id: string
  deck_slug: string
  prompt: string
  scene?: Scene | null
  target_ms: number
  is_new: boolean
  answer_type: 'flip'
  back_md: string
}
export type QueueCounts = {
  due: number
  new: number
  reviewed: number
}
export type NextOut = {
  problem:
    | (
        | ({
            answer_type: 'action'
          } & ActionProblem)
        | ({
            answer_type: 'bucket'
          } & BucketProblem)
        | ({
            answer_type: 'choice'
          } & ChoiceProblem)
        | ({
            answer_type: 'flip'
          } & FlipProblem)
      )
    | null
  queue: QueueCounts
}
export type DeckStat = {
  deck_id: string
  deck_name: string
  reviews: number
  accuracy: number
  median_latency_ms: number
}
export type SessionSummaryOut = {
  session_id: string
  mode: 'review' | 'drill' | 'learn'
  reviewed: number
  correct: number
  accuracy: number
  median_latency_ms: number
  duration_s: number
  by_deck: DeckStat[]
}
export type GradeOut = {
  instance_id: string
  is_correct: boolean | null
  rating: 'again' | 'hard' | 'good' | 'easy'
  correct_response: number | ('fold' | 'call' | 'raise') | null
  exact_answer: number | string | null
  back_md: string | null
  shortcut: string
  explanation_md: string
  latency_ms: number
  target_ms: number
  next_due: string | null
}
export type AnswerIn = {
  response?: number | ('fold' | 'call' | 'raise') | null
  self_rating?: ('again' | 'hard' | 'good' | 'easy') | null
  latency_ms: number
}
export type TutorOut = {
  message_md: string
}
export type TutorIn = {
  question?: string | null
}
export type ConfigOut = {
  tutor_enabled: boolean
}
export type DayStat = {
  date: string
  reviews: number
  correct: number
}
export type DeckStatRow = {
  deck_id: string
  deck_name: string
  section: number
  reviews: number
  accuracy: number
  median_latency_ms: number
  on_time: number
  mastery: number
}
export type StatsOverviewOut = {
  streak_days: number
  reviews_today: number
  due_now: number
  reviews_7d: number
  accuracy_7d: number | null
  median_latency_ms_7d: number | null
  daily: DayStat[]
  decks: DeckStatRow[]
  weakest: DeckStatRow[]
}
export type CardStatRow = {
  card_id: string
  slug: string
  label: string
  answer_type: string
  reviews: number
  accuracy: number | null
  median_latency_ms: number | null
  target_ms: number
  state: string
  due: string | null
  stability_days: number | null
}
export type DeckStatsOut = {
  deck_id: string
  deck_name: string
  cards: CardStatRow[]
}
export const {
  useGetHealthQuery,
  useGetSettingsQuery,
  useUpdateSettingsMutation,
  useListPacksQuery,
  useGetPackQuery,
  useGetDeckQuery,
  useCreateSessionMutation,
  useNextProblemMutation,
  useEndSessionMutation,
  useAnswerProblemMutation,
  useTutorExplainMutation,
  useGetConfigQuery,
  useGetStatsOverviewQuery,
  useGetDeckStatsQuery,
} = injectedRtkApi
