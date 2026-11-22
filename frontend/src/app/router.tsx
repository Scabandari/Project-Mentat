import { createBrowserRouter } from 'react-router'

import { HomePage } from '@/pages/HomePage'
import { StudyPage } from '@/pages/StudyPage'

export const router = createBrowserRouter([
  { path: '/', element: <HomePage /> },
  { path: '/study/:sessionId', element: <StudyPage /> },
])
