import { useEffect } from 'react'

import { cn } from '@/lib/utils'

export type Response = number | 'fold' | 'call' | 'raise'

export interface Option {
  value: Response
  label: string
}

interface Props {
  options: Option[]
  selected: Response | null
  correct: Response | null // known after grading
  disabled: boolean
  onSelect: (r: Response) => void
  layout: 'stack' | 'row'
}

/** Shared input for bucket, choice and action answers. Keys 1–9 select by position. */
export function AnswerOptions({ options, selected, correct, disabled, onSelect, layout }: Props) {
  useEffect(() => {
    if (disabled) return
    function onKey(e: KeyboardEvent) {
      const i = Number(e.key) - 1
      const opt = Number.isInteger(i) ? options[i] : undefined
      if (opt) onSelect(opt.value)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [disabled, options, onSelect])

  const graded = correct !== null
  return (
    <div
      role="group"
      aria-label="Answer"
      className={cn(
        layout === 'row' ? 'grid auto-cols-fr grid-flow-col gap-2' : 'flex flex-col gap-2',
      )}
    >
      {options.map((o, i) => {
        const isCorrect = graded && o.value === correct
        const isWrongPick = graded && o.value === selected && o.value !== correct
        return (
          <button
            key={String(o.value)}
            type="button"
            disabled={disabled}
            aria-pressed={selected === o.value}
            onClick={() => onSelect(o.value)}
            className={cn(
              'flex min-h-12 items-center justify-between rounded-xl border px-4 py-3 text-left text-base font-medium tabular-nums transition-colors',
              !graded && 'bg-card hover:bg-accent active:scale-[0.99]',
              isCorrect && 'border-emerald-500 bg-emerald-500/15 text-emerald-200',
              isWrongPick && 'border-red-500 bg-red-500/15 text-red-200',
              graded && !isCorrect && !isWrongPick && 'opacity-50',
              layout === 'row' && 'justify-center capitalize',
            )}
          >
            <span>{o.label}</span>
            {layout === 'stack' && <span className="text-muted-foreground text-xs">{i + 1}</span>}
          </button>
        )
      })}
    </div>
  )
}
