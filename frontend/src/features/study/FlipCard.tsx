import { useEffect } from 'react'

import type { FlipProblem } from '@/api'
import { Markdown } from '@/components/Markdown'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { TargetTimer } from './TargetTimer'

export type SelfRating = 'again' | 'hard' | 'good' | 'easy'

const RATINGS: { value: SelfRating; label: string; key: string; className: string }[] = [
  {
    value: 'again',
    label: 'Again',
    key: '1',
    className: 'bg-red-500/15 text-red-300 hover:bg-red-500/25',
  },
  {
    value: 'hard',
    label: 'Hard',
    key: '2',
    className: 'bg-amber-500/15 text-amber-300 hover:bg-amber-500/25',
  },
  {
    value: 'good',
    label: 'Good',
    key: '3',
    className: 'bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25',
  },
  {
    value: 'easy',
    label: 'Easy',
    key: '4',
    className: 'bg-sky-500/15 text-sky-300 hover:bg-sky-500/25',
  },
]

export function FlipCard({
  problem,
  revealed,
  busy,
  showTimer,
  onReveal,
  onRate,
}: {
  problem: FlipProblem
  revealed: boolean
  busy: boolean
  showTimer: boolean
  onReveal: () => void
  onRate: (r: SelfRating) => void
}) {
  // Keyboard: Space/Enter reveals, 1–4 rate.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (busy) return
      if (!revealed && (e.key === ' ' || e.key === 'Enter')) {
        e.preventDefault()
        onReveal()
      } else if (revealed) {
        const r = RATINGS.find((x) => x.key === e.key)
        if (r) onRate(r.value)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, revealed, onReveal, onRate])

  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="text-muted-foreground flex items-center justify-between text-xs">
        <span className="tracking-wide uppercase">{problem.deck_slug.replaceAll('-', ' ')}</span>
        {problem.is_new && (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-emerald-300">New</span>
        )}
      </div>

      {showTimer && <TargetTimer targetMs={problem.target_ms} running={!revealed} />}

      <div className="bg-card flex min-h-48 flex-col justify-center rounded-2xl border p-6">
        <Markdown className="text-lg">{problem.prompt}</Markdown>
        {revealed && (
          <>
            <hr className="border-border my-4" />
            <Markdown>{problem.back_md}</Markdown>
          </>
        )}
      </div>

      <div className="mt-auto">
        {revealed ? (
          <div className="grid grid-cols-4 gap-2">
            {RATINGS.map((r) => (
              <button
                key={r.value}
                type="button"
                disabled={busy}
                onClick={() => onRate(r.value)}
                className={cn(
                  'flex h-14 flex-col items-center justify-center rounded-xl text-sm font-medium transition-colors disabled:opacity-50',
                  r.className,
                )}
              >
                {r.label}
                <span className="text-[10px] opacity-60">{r.key}</span>
              </button>
            ))}
          </div>
        ) : (
          <Button size="lg" className="h-14 w-full text-base" disabled={busy} onClick={onReveal}>
            Show answer
          </Button>
        )}
      </div>
    </div>
  )
}
