import { X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import {
  type NextOut,
  type SessionSummaryOut,
  useAnswerProblemMutation,
  useEndSessionMutation,
  useGetSettingsQuery,
  useNextProblemMutation,
} from '@/api'
import { useAppDispatch, useAppSelector } from '@/app/hooks'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { FlipCard, type SelfRating } from '@/features/study/FlipCard'
import { SessionSummary } from '@/features/study/SessionSummary'
import {
  answerRevealed,
  gradeReceived,
  gradingStarted,
  nextRequested,
  problemShown,
  queueEmptied,
  selectFlipLatency,
  sessionStarted,
} from '@/features/study/studySlice'

export function StudyPage() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const study = useAppSelector((s) => s.study)
  const latency = useAppSelector(selectFlipLatency)
  const { data: settings } = useGetSettingsQuery()

  const [nextProblem] = useNextProblemMutation()
  const [answerProblem] = useAnswerProblemMutation()
  const [endSession] = useEndSessionMutation()
  const [current, setCurrent] = useState<NextOut | null>(null)
  const [summary, setSummary] = useState<SessionSummaryOut | null>(null)
  const [error, setError] = useState<string | null>(null)

  const finish = useCallback(async () => {
    const s = await endSession({ sessionId }).unwrap()
    dispatch(queueEmptied())
    setSummary(s)
  }, [dispatch, endSession, sessionId])

  const loadNext = useCallback(async () => {
    dispatch(nextRequested())
    try {
      const res = await nextProblem({ sessionId }).unwrap()
      setCurrent(res)
      if (res.problem) {
        dispatch(problemShown({ instanceId: res.problem.instance_id, at: performance.now() }))
      } else {
        await finish()
      }
    } catch {
      setError('Couldn’t load the next card.')
    }
  }, [dispatch, finish, nextProblem, sessionId])

  useEffect(() => {
    dispatch(sessionStarted(sessionId))
    // Fetching the first card is the external sync this effect exists for. `next` is
    // idempotent server-side, so StrictMode's double-run returns the same card.
    // oxlint-disable-next-line react/set-state-in-effect
    void loadNext()
  }, [dispatch, loadNext, sessionId])

  async function rate(self_rating: SelfRating) {
    const problem = current?.problem
    if (!problem || study.phase !== 'revealed') return
    dispatch(gradingStarted())
    const grade = await answerProblem({
      instanceId: problem.instance_id,
      answerIn: { self_rating, latency_ms: latency },
    }).unwrap()
    dispatch(gradeReceived(grade))
    await loadNext()
  }

  async function quit() {
    if (summary) return navigate('/')
    await finish()
  }

  if (error) {
    return (
      <Shell onClose={() => navigate('/')}>
        <p className="text-destructive">{error}</p>
      </Shell>
    )
  }

  if (summary) {
    return (
      <Shell onClose={() => navigate('/')}>
        <SessionSummary summary={summary} />
        <Button asChild size="lg" className="mt-6 w-full">
          <Link to="/">Done</Link>
        </Button>
      </Shell>
    )
  }

  const q = current?.queue
  const remaining = q ? q.due + q.new : 0
  const total = q ? q.reviewed + remaining : 0
  const problem = current?.problem

  return (
    <Shell
      onClose={() => void quit()}
      progress={total ? (q!.reviewed / total) * 100 : 0}
      counter={q ? `${q.reviewed} / ${total}` : undefined}
    >
      {problem?.answer_type === 'flip' ? (
        <FlipCard
          key={problem.instance_id}
          problem={problem}
          revealed={study.phase === 'revealed' || study.phase === 'grading'}
          busy={study.phase === 'grading' || study.phase === 'loading'}
          showTimer={settings?.show_timer ?? true}
          onReveal={() => dispatch(answerRevealed({ at: performance.now() }))}
          onRate={(r) => void rate(r)}
        />
      ) : problem ? (
        <p className="text-muted-foreground">This card type arrives in M2.</p>
      ) : (
        <p className="text-muted-foreground">Loading…</p>
      )}
    </Shell>
  )
}

function Shell({
  children,
  onClose,
  progress,
  counter,
}: {
  children: React.ReactNode
  onClose: () => void
  progress?: number
  counter?: string
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 p-5">
      <div className="flex items-center gap-3">
        <Button size="icon" variant="ghost" aria-label="End session" onClick={onClose}>
          <X />
        </Button>
        {progress !== undefined && <Progress value={progress} className="flex-1" />}
        {counter && <span className="text-muted-foreground text-xs tabular-nums">{counter}</span>}
      </div>
      <div className="flex flex-1 flex-col">{children}</div>
    </main>
  )
}
