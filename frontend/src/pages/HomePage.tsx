import { Dumbbell, Play } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import {
  type DeckOut,
  type SessionIn,
  useCreateSessionMutation,
  useGetPackQuery,
  useGetSettingsQuery,
  useUpdateSettingsMutation,
} from '@/api'
import { SegmentedToggle } from '@/components/SegmentedToggle'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

const PACK = 'poker-math'

export function HomePage() {
  const navigate = useNavigate()
  const { data: pack, isLoading, isError } = useGetPackQuery({ slug: PACK })
  const { data: settings } = useGetSettingsQuery()
  const [updateSettings, { isLoading: savingSettings }] = useUpdateSettingsMutation()
  const [createSession, { isLoading: starting }] = useCreateSessionMutation()

  async function start(sessionIn: SessionIn) {
    const s = await createSession({ sessionIn }).unwrap()
    navigate(`/study/${s.id}`)
  }

  const studyable = (pack?.due_count ?? 0) + (pack?.new_today ?? 0)

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-5 p-5 pb-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Mentat</h1>
          <p className="text-muted-foreground text-sm">Poker math, at the speed of thought.</p>
        </div>
        <SegmentedToggle
          label="Stakes format"
          value={settings?.stakes_format ?? 'online'}
          disabled={savingSettings || !settings}
          onChange={(stakes_format) => void updateSettings({ settingsIn: { stakes_format } })}
          options={[
            { value: 'live', label: 'Live' },
            { value: 'online', label: 'Online' },
          ]}
        />
      </header>

      {isError && (
        <p className="border-destructive/40 text-destructive rounded-lg border p-4 text-sm">
          Can’t reach the API.
        </p>
      )}

      <Card className="gap-4">
        <CardHeader>
          <CardTitle>Today</CardTitle>
          <CardDescription>
            {isLoading
              ? 'Loading…'
              : studyable
                ? 'Reviews first, then new cards.'
                : 'All caught up. Drill a deck to keep sharp.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-end justify-between gap-4">
          <div className="flex gap-6">
            <Stat label="Due" value={pack?.due_count} accent="text-sky-400" />
            <Stat label="New" value={pack?.new_today} accent="text-emerald-400" />
          </div>
          <Button
            size="lg"
            disabled={!studyable || starting}
            onClick={() => void start({ mode: 'review' })}
          >
            <Play /> Study
          </Button>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-2">
        <h2 className="text-muted-foreground px-1 text-sm font-medium">Sections</h2>
        {pack?.decks.map((deck) => (
          <DeckRow
            key={deck.id}
            deck={deck}
            newAllowed={(pack.new_today ?? 0) > 0}
            disabled={starting}
            onStudy={() => void start({ mode: 'review', deck_ids: [deck.id] })}
            onDrill={() => void start({ mode: 'drill', deck_ids: [deck.id] })}
          />
        ))}
      </section>
    </main>
  )
}

function Stat({ label, value, accent }: { label: string; value?: number; accent: string }) {
  return (
    <div>
      <div className={cn('text-3xl font-semibold tabular-nums', accent)}>{value ?? '–'}</div>
      <div className="text-muted-foreground text-xs tracking-wide uppercase">{label}</div>
    </div>
  )
}

function DeckRow({
  deck,
  newAllowed,
  disabled,
  onStudy,
  onDrill,
}: {
  deck: DeckOut
  newAllowed: boolean
  disabled: boolean
  onStudy: () => void
  onDrill: () => void
}) {
  const empty = deck.card_count === 0
  // New cards are only studyable while today's new-card allowance remains.
  const studyable = deck.due_count > 0 || (newAllowed && deck.new_count > 0)
  return (
    <div
      className={cn(
        'bg-card relative flex items-center gap-3 rounded-xl border p-3 [&_button]:relative [&_button]:z-10',
        empty && 'opacity-50',
      )}
    >
      <div className="bg-secondary flex size-9 shrink-0 items-center justify-center rounded-lg text-sm font-semibold tabular-nums">
        {deck.section}
      </div>
      <div className="min-w-0 flex-1">
        <Link
          to={`/decks/${deck.id}`}
          className={cn(
            'block truncate font-medium after:absolute after:inset-0',
            deck.locked && 'text-muted-foreground',
          )}
          title={deck.locked ? 'Recommended after the previous section' : undefined}
        >
          {deck.name}
        </Link>
        <div className="mt-1.5 flex items-center gap-2">
          <Progress
            value={deck.mastery * 100}
            className="h-1"
            aria-label={`${deck.name} mastery`}
          />
          <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
            {empty ? 'soon' : `${deck.due_count} due · ${deck.new_count} new`}
          </span>
        </div>
      </div>
      <Button
        size="icon"
        variant="ghost"
        aria-label={`Drill ${deck.name}`}
        disabled={empty || disabled}
        onClick={onDrill}
      >
        <Dumbbell />
      </Button>
      <Button
        size="icon"
        variant="secondary"
        aria-label={`Study ${deck.name}`}
        disabled={!studyable || disabled}
        onClick={onStudy}
      >
        <Play />
      </Button>
    </div>
  )
}
