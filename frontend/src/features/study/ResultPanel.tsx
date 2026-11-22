import { Check, Sparkles, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { type GradeOut, useGetConfigQuery, useTutorExplainMutation } from '@/api'
import { Markdown } from '@/components/Markdown'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const RATING_LABEL: Record<GradeOut['rating'], string> = {
  again: 'Again',
  hard: 'Correct, but slow',
  good: 'Correct',
  easy: 'Correct and fast',
}

export function ResultPanel({
  grade,
  unit,
  onContinue,
}: {
  grade: GradeOut
  unit?: string | null
  onContinue: () => void
}) {
  const [showWhy, setShowWhy] = useState(!grade.is_correct)
  const { data: config } = useGetConfigQuery()
  const [askTutor, tutor] = useTutorExplainMutation()

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        onContinue()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onContinue])

  const secs = (grade.latency_ms / 1000).toFixed(1)
  const target = (grade.target_ms / 1000).toFixed(0)
  const slow = grade.latency_ms > grade.target_ms

  return (
    <div className="flex flex-col gap-3" aria-live="polite">
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl px-4 py-3 font-medium',
          grade.is_correct ? 'bg-emerald-500/15 text-emerald-200' : 'bg-red-500/15 text-red-200',
        )}
      >
        {grade.is_correct ? <Check className="size-5" /> : <X className="size-5" />}
        <span className="flex-1">
          {grade.is_correct ? RATING_LABEL[grade.rating] : 'Not quite'}
        </span>
        <span className={cn('text-sm tabular-nums', slow && 'text-amber-300')}>
          {secs}s / {target}s
        </span>
      </div>

      {grade.exact_answer !== null && (
        <p className="text-muted-foreground text-sm">
          Exact answer:{' '}
          <span className="text-foreground font-semibold">
            {formatExact(grade.exact_answer, unit)}
          </span>
        </p>
      )}

      <p className="bg-secondary rounded-lg px-3 py-2 text-sm">
        <span className="font-semibold">Shortcut:</span> {grade.shortcut}
      </p>

      {showWhy ? (
        <div className="bg-card rounded-xl border p-4">
          <Markdown className="text-sm">{grade.explanation_md}</Markdown>
        </div>
      ) : (
        <button
          type="button"
          className="text-muted-foreground self-start text-sm underline underline-offset-4"
          onClick={() => setShowWhy(true)}
        >
          Show the working
        </button>
      )}

      {config?.tutor_enabled && (
        <div className="flex flex-col gap-2">
          {tutor.data ? (
            <div className="rounded-xl border border-violet-500/30 bg-violet-500/10 p-4">
              <Markdown className="text-sm">{tutor.data.message_md}</Markdown>
            </div>
          ) : (
            <Button
              variant="outline"
              disabled={tutor.isLoading}
              onClick={() => void askTutor({ instanceId: grade.instance_id, tutorIn: {} })}
            >
              <Sparkles /> {tutor.isLoading ? 'Thinking…' : 'Explain differently'}
            </Button>
          )}
          {tutor.isError && (
            <p className="text-destructive text-sm">Tutor unavailable right now.</p>
          )}
        </div>
      )}

      <Button size="lg" className="mt-2 h-14 text-base" onClick={onContinue}>
        Continue
      </Button>
    </div>
  )
}

function formatExact(x: number | string, unit?: string | null) {
  if (typeof x === 'number') return unit === 'percent' ? `${x}%` : String(x)
  return x.charAt(0).toUpperCase() + x.slice(1)
}
