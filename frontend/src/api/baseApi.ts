import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

// Endpoints are injected by the generated client (src/api/generated.ts). Run `make gen-api`.
export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: window.location.origin }),
  endpoints: () => ({}),
})
