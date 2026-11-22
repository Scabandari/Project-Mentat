import { useEffect, useState } from 'react'

import { cn } from '@/lib/utils'

/** Bar that fills toward the card's target time: green within target, amber up to 2×, then red. */
export function TargetTimer({ targetMs, running }: { targetMs: number; running: boolean }) {
  const [start] = useState(() => performance.now())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!running) return
    let raf = 0
    const tick = () => {
      setElapsed(performance.now() - start)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [running, start])

  const ratio = elapsed / targetMs
  const color = ratio <= 1 ? 'bg-emerald-400' : ratio <= 2 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2" aria-hidden>
      <div className="bg-secondary h-1 flex-1 overflow-hidden rounded-full">
        <div
          className={cn('h-full transition-colors', color)}
          style={{ width: `${Math.min(100, (ratio / 2) * 100)}%` }}
        />
      </div>
      <span className="text-muted-foreground w-10 text-right text-xs tabular-nums">
        {(elapsed / 1000).toFixed(1)}s
      </span>
    </div>
  )
}
