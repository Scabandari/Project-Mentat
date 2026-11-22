import type { Scene } from '@/api'
import { formatMoney } from '@/lib/format'

import { CardRow } from './PlayingCard'

export function SceneView({ scene }: { scene: Scene }) {
  const hasCards = Boolean(scene.board?.length || scene.hero?.length || scene.villain?.length)
  const hasMoney = scene.pot != null
  const stacks = [
    scene.hero_stack != null ? `You ${formatMoney(scene.hero_stack, scene.money_format)}` : null,
    scene.villain_stack != null
      ? `Villain ${formatMoney(scene.villain_stack, scene.money_format)}`
      : null,
  ].filter(Boolean)
  if (!hasCards && !hasMoney) return null
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl bg-emerald-950/40 p-4 ring-1 ring-emerald-900/50">
      {scene.villain?.length ? <CardRow cards={scene.villain} label="Villain" size="sm" /> : null}
      {scene.board?.length ? (
        <CardRow cards={scene.board} label={scene.street ? `Board · ${scene.street}` : 'Board'} />
      ) : null}
      {hasMoney && (
        <div className="flex gap-2 text-xs tabular-nums">
          <span className="rounded-full bg-black/30 px-2.5 py-1">
            Pot {formatMoney(scene.pot!, scene.money_format)}
          </span>
          {scene.bet != null && (
            <span className="rounded-full bg-amber-500/20 px-2.5 py-1 text-amber-200">
              Bet {formatMoney(scene.bet, scene.money_format)}
            </span>
          )}
          {stacks.map((s) => (
            <span key={s} className="rounded-full bg-sky-500/15 px-2.5 py-1 text-sky-200">
              {s}
            </span>
          ))}
        </div>
      )}
      {scene.hero?.length ? <CardRow cards={scene.hero} label="You" /> : null}
    </div>
  )
}
