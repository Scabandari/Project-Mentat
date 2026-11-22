import type { ActionProblem, BucketProblem, ChoiceProblem, GradeOut } from '@/api'
import { Markdown } from '@/components/Markdown'

import { AnswerOptions, type Option, type Response } from './AnswerInputs'
import { ResultPanel } from './ResultPanel'
import { SceneView } from './SceneView'
import { TargetTimer } from './TargetTimer'

export type AutoGradedProblem = BucketProblem | ChoiceProblem | ActionProblem

function optionsFor(p: AutoGradedProblem): Option[] {
  switch (p.answer_type) {
    case 'bucket':
      return p.buckets.map((b) => ({ value: b.id, label: b.label }))
    case 'choice':
      return p.choices.map((c) => ({ value: c.id, label: c.label }))
    case 'action':
      return p.actions.map((a) => ({ value: a, label: a }))
  }
}

export function GeneratedCard({
  problem,
  selected,
  grade,
  busy,
  showTimer,
  onAnswer,
  onContinue,
}: {
  problem: AutoGradedProblem
  selected: Response | null
  grade: GradeOut | null
  busy: boolean
  showTimer: boolean
  onAnswer: (r: Response) => void
  onContinue: () => void
}) {
  const answered = selected !== null
  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="text-muted-foreground flex items-center justify-between text-xs">
        <span className="tracking-wide uppercase">{problem.deck_slug.replaceAll('-', ' ')}</span>
        {problem.is_new && (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-emerald-300">New</span>
        )}
      </div>

      {showTimer && <TargetTimer targetMs={problem.target_ms} running={!answered} />}

      {problem.scene && <SceneView scene={problem.scene} />}

      <Markdown className="text-lg">{problem.prompt}</Markdown>

      <AnswerOptions
        options={optionsFor(problem)}
        selected={selected}
        correct={(grade?.correct_response as Response | undefined) ?? null}
        disabled={answered || busy}
        onSelect={onAnswer}
        layout={problem.answer_type === 'action' ? 'row' : 'stack'}
      />

      {grade && (
        <ResultPanel
          grade={grade}
          unit={problem.answer_type === 'bucket' ? problem.unit : null}
          onContinue={onContinue}
        />
      )}
    </div>
  )
}
