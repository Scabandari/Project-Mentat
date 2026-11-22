import { baseApi as api } from './baseApi'
export const addTagTypes = ['health'] as const
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
    }),
    overrideExisting: false,
  })
export { injectedRtkApi as mentatApi }
export type GetHealthApiResponse = /** status 200 Successful Response */ HealthOut
export type GetHealthApiArg = void
export type HealthOut = {
  status: 'ok' | 'degraded'
  db: 'ok' | 'down'
  version: string
}
export const { useGetHealthQuery } = injectedRtkApi
