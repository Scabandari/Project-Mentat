import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { RouterProvider } from 'react-router'

import { router } from '@/app/router'
import { makeStore } from '@/app/store'

import './index.css'

document.documentElement.classList.add('dark')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={makeStore()}>
      <RouterProvider router={router} />
    </Provider>
  </StrictMode>,
)
