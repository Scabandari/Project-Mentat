import { ArrowLeft, BookOpen, Dumbbell, Play } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router'

import { type SessionIn, useCreateSessionMutation, useGetDeckQuery, useGetPackQuery } from '@/api'
import { Markdown } from '@/components/Markdown'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { CardStats } from '@/features/stats/CardStats'

export function DeckPage() {
  const { deckId = '' } = useParams()
  const navigate = useNavigate()
  const { data: deck, isLoading, isError } = useGetDeckQuery({ deckId })
  const { data: pack } = useGetPackQuery({ slug: 'poker-math' })
  const [createSession, { isLoading: starting }] = useCreateSessionMutation()

  async function start(sessionIn: SessionIn) {
    const s = await createSession({ sessionIn: { ...sessionIn, deck_ids: [deckId] } }).unwrap()
    navigate(`/study/${s.id}`)
  }

  if (isError) return <p className="text-destructive p-6">Deck not found.</p>
  if (isLoading || !deck) return <p className="text-muted-foreground p-6">Loading…</p>

  const newToday = Math.min(deck.new_count, pack?.new_today ?? 0)

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-5 p-5 pb-32">
      <header className="flex items-start gap-2">
        <Button asChild size="icon" variant="ghost" aria-label="Back">
          <Link to="/">
            <ArrowLeft />
          </Link>
        </Button>
        <div className="flex-1">
          <p className="text-muted-foreground text-xs tracking-wide uppercase">
            Section {deck.section}
          </p>
          <h1 className="text-2xl font-bold tracking-tight">{deck.name}</h1>
          <p className="text-muted-foreground text-sm">{deck.description}</p>
        </div>
      </header>

      <div className="flex flex-col gap-2">
        <div className="text-muted-foreground flex justify-between text-sm tabular-nums">
          <span>{Math.round(deck.mastery * 100)}% mastered</span>
          <span>
            {deck.card_count} cards · {deck.due_count} due · {deck.new_count} new
          </span>
        </div>
        <Progress value={deck.mastery * 100} />
      </div>

      {deck.lesson_md ? (
        <article className="bg-card rounded-2xl border p-5">
          <div className="text-muted-foreground mb-2 flex items-center gap-2 text-sm">
            <BookOpen className="size-4" /> Lesson
          </div>
          <Markdown className="prose-sm prose-table:text-sm">{deck.lesson_md}</Markdown>
        </article>
      ) : (
        <p className="text-muted-foreground text-sm">Lesson coming soon.</p>
      )}

      <CardStats deckId={deckId} />

      <div className="bg-background/95 fixed inset-x-0 bottom-0 border-t p-4 backdrop-blur">
        <div className="mx-auto grid max-w-md grid-cols-3 gap-2">
          <Button
            size="lg"
            disabled={starting || deck.new_count === 0}
            onClick={() => void start({ mode: 'learn' })}
          >
            <BookOpen /> Learn
          </Button>
          <Button
            size="lg"
            variant="secondary"
            disabled={starting || deck.due_count + newToday === 0}
            onClick={() => void start({ mode: 'review' })}
          >
            <Play /> Review
          </Button>
          <Button
            size="lg"
            variant="secondary"
            disabled={starting || deck.card_count === 0}
            onClick={() => void start({ mode: 'drill' })}
          >
            <Dumbbell /> Drill
          </Button>
        </div>
      </div>
    </main>
  )
}
