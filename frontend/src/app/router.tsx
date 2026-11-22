import { createBrowserRouter } from 'react-router'

import { DeckPage } from '@/pages/DeckPage'
import { HomePage } from '@/pages/HomePage'
import { StudyPage } from '@/pages/StudyPage'

export const router = createBrowserRouter([
  { path: '/', element: <HomePage /> },
  { path: '/decks/:deckId', element: <DeckPage /> },
  { path: '/study/:sessionId', element: <StudyPage /> },
])
