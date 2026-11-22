import { useState } from 'react'

import { type CardStatRow, useGetDeckStatsQuery } from '@/api'
import { cn } from '@/lib/utils'

const STATE_STYLE: Record<string, string> = {
  new: 'bg-secondary text-muted-foreground',
  learning: 'bg-amber-500/15 text-amber-300',
  relearning: 'bg-red-500/15 text-red-300',
  review: 'bg-emerald-500/15 text-emerald-300',
}

export function CardStats({ deckId }: { deckId: string }) {
  const [open, setOpen] = useState(false)
  const { data } = useGetDeckStatsQuery({ deckId }, { skip: !open })
  return (
    <section className="flex flex-col gap-2">
      <button
        type="button"
        className="text-muted-foreground self-start text-sm underline underline-offset-4"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {open ? 'Hide card stats' : 'Show card stats'}
      </button>
      {open && data && (
        <ul className="flex flex-col divide-y rounded-xl border text-sm">
          {data.cards.map((c) => (
            <Row key={c.card_id} c={c} />
          ))}
        </ul>
      )}
    </section>
  )
}

function Row({ c }: { c: CardStatRow }) {
  return (
    <li className="flex items-center gap-2 p-3">
      <span className="min-w-0 flex-1 truncate" title={c.label}>
        {c.label}
      </span>
      {c.reviews > 0 && (
        <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
          {c.reviews}× · {Math.round((c.accuracy ?? 0) * 100)}%
          {c.median_latency_ms != null && ` · ${(c.median_latency_ms / 1000).toFixed(1)}s`}
        </span>
      )}
      <span
        className={cn(
          'shrink-0 rounded-full px-2 py-0.5 text-[10px] uppercase',
          STATE_STYLE[c.state],
        )}
      >
        {c.state}
      </span>
    </li>
  )
}
