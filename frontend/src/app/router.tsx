import { createBrowserRouter } from 'react-router'

import { DeckPage } from '@/pages/DeckPage'
import { HomePage } from '@/pages/HomePage'
import { StatsPage } from '@/pages/StatsPage'
import { StudyPage } from '@/pages/StudyPage'

export const router = createBrowserRouter([
  { path: '/', element: <HomePage /> },
  { path: '/decks/:deckId', element: <DeckPage /> },
  { path: '/stats', element: <StatsPage /> },
  { path: '/study/:sessionId', element: <StudyPage /> },
])
