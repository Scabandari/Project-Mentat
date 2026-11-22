import { ArrowLeft, Dumbbell, Flame } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { type DeckStatRow, useCreateSessionMutation, useGetStatsOverviewQuery } from '@/api'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)
const secs = (ms: number | null | undefined) => (ms == null ? '–' : `${(ms / 1000).toFixed(1)}s`)

export function StatsPage() {
  const navigate = useNavigate()
  const { data: s, isLoading, isError } = useGetStatsOverviewQuery()
  const [createSession, { isLoading: starting }] = useCreateSessionMutation()

  async function drill(deckId: string) {
    const session = await createSession({
      sessionIn: { mode: 'drill', deck_ids: [deckId] },
    }).unwrap()
    navigate(`/study/${session.id}`)
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-5 p-5 pb-10">
      <header className="flex items-center gap-2">
        <Button asChild size="icon" variant="ghost" aria-label="Back">
          <Link to="/">
            <ArrowLeft />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Progress</h1>
      </header>

      {isError && <p className="text-destructive">Couldn’t load stats.</p>}
      {isLoading || !s ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Tile
              label="Day streak"
              value={String(s.streak_days)}
              icon={
                <Flame
                  className={cn(
                    'size-5',
                    s.streak_days ? 'text-orange-400' : 'text-muted-foreground',
                  )}
                />
              }
            />
            <Tile label="Today" value={String(s.reviews_today)} />
            <Tile label="Accuracy · 7d" value={pct(s.accuracy_7d)} />
            <Tile label="Median time · 7d" value={secs(s.median_latency_ms_7d)} />
          </div>

          <section className="flex flex-col gap-2">
            <h2 className="text-muted-foreground text-sm font-medium">Last 14 days</h2>
            <DailyBars days={s.daily} />
          </section>

          {s.weakest.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-muted-foreground text-sm font-medium">Needs work</h2>
              {s.weakest.map((d) => (
                <div
                  key={d.deck_id}
                  className="bg-card flex items-center gap-3 rounded-xl border p-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{d.deck_name}</div>
                    <div className="text-muted-foreground text-xs tabular-nums">
                      {pct(d.accuracy)} right · {pct(d.on_time)} on time
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={starting}
                    onClick={() => void drill(d.deck_id)}
                  >
                    <Dumbbell /> Drill
                  </Button>
                </div>
              ))}
            </section>
          )}

          <section className="flex flex-col gap-2">
            <h2 className="text-muted-foreground text-sm font-medium">By section · last 30 days</h2>
            {s.decks.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No reviews yet. Study a few cards first.
              </p>
            ) : (
              <div className="flex flex-col divide-y rounded-xl border">
                {s.decks.map((d) => (
                  <DeckRow key={d.deck_id} d={d} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  )
}

function Tile({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="bg-card rounded-xl border p-3">
      <div className="flex items-center gap-1.5 text-2xl font-semibold tabular-nums">
        {icon}
        {value}
      </div>
      <div className="text-muted-foreground text-xs tracking-wide uppercase">{label}</div>
    </div>
  )
}

function DailyBars({ days }: { days: { date: string; reviews: number; correct: number }[] }) {
  const max = Math.max(1, ...days.map((d) => d.reviews))
  return (
    <div
      className="bg-card flex h-28 items-end gap-1 rounded-xl border p-3"
      role="img"
      aria-label="Reviews per day"
    >
      {days.map((d) => (
        <div
          key={d.date}
          className="flex h-full flex-1 flex-col justify-end"
          title={`${d.date}: ${d.reviews} reviews, ${d.correct} right`}
        >
          <div
            className="flex flex-col overflow-hidden rounded-sm"
            style={{ height: `${(d.reviews / max) * 100}%` }}
          >
            <div className="bg-red-400/60" style={{ flexGrow: d.reviews - d.correct }} />
            <div className="bg-emerald-400" style={{ flexGrow: d.correct }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function DeckRow({ d }: { d: DeckStatRow }) {
  return (
    <Link to={`/decks/${d.deck_id}`} className="hover:bg-accent/40 flex flex-col gap-1.5 p-3">
      <div className="flex justify-between text-sm">
        <span className="font-medium">
          <span className="text-muted-foreground mr-2 tabular-nums">{d.section}</span>
          {d.deck_name}
        </span>
        <span className="text-muted-foreground tabular-nums">
          {d.reviews} · {pct(d.accuracy)} · {secs(d.median_latency_ms)}
        </span>
      </div>
      <Progress value={d.mastery * 100} className="h-1" aria-label={`${d.deck_name} mastery`} />
    </Link>
  )
}
