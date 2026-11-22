import { combineReducers, configureStore } from '@reduxjs/toolkit'

import { baseApi } from '@/api/baseApi'
import settingsReducer from '@/features/settings/settingsSlice'

const rootReducer = combineReducers({
  settings: settingsReducer,
  [baseApi.reducerPath]: baseApi.reducer,
})

export function makeStore(preloadedState?: Partial<RootState>) {
  return configureStore({
    reducer: rootReducer,
    preloadedState,
    middleware: (getDefault) => getDefault().concat(baseApi.middleware),
  })
}

export type RootState = ReturnType<typeof rootReducer>
export type AppStore = ReturnType<typeof makeStore>
export type AppDispatch = AppStore['dispatch']
