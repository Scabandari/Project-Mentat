import type { SessionSummaryOut } from '@/api'

function fmtDuration(s: number) {
  const m = Math.floor(s / 60)
  return m ? `${m}m ${s % 60}s` : `${s}s`
}

export function SessionSummary({ summary }: { summary: SessionSummaryOut }) {
  if (summary.reviewed === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
        <h2 className="text-2xl font-semibold">Nothing to review</h2>
        <p className="text-muted-foreground">You’re all caught up.</p>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-semibold">Session complete</h2>
      <div className="grid grid-cols-3 gap-3">
        <Tile label="Cards" value={String(summary.reviewed)} />
        <Tile label="Recalled" value={`${Math.round(summary.accuracy * 100)}%`} />
        <Tile label="Median" value={`${(summary.median_latency_ms / 1000).toFixed(1)}s`} />
      </div>
      <p className="text-muted-foreground text-sm">
        {fmtDuration(summary.duration_s)} · {summary.mode}
      </p>
      <ul className="flex flex-col divide-y rounded-xl border">
        {summary.by_deck.map((d) => (
          <li key={d.deck_id} className="flex items-center justify-between p-3 text-sm">
            <span>{d.deck_name}</span>
            <span className="text-muted-foreground tabular-nums">
              {d.reviews} · {Math.round(d.accuracy * 100)}% ·{' '}
              {(d.median_latency_ms / 1000).toFixed(1)}s
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card rounded-xl border p-3">
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-muted-foreground text-xs tracking-wide uppercase">{label}</div>
    </div>
  )
}
