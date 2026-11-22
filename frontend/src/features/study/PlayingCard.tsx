import { cn } from '@/lib/utils'

const SUIT: Record<string, { symbol: string; className: string; name: string }> = {
  s: { symbol: '♠', className: 'bg-zinc-800 text-zinc-50', name: 'spades' },
  h: { symbol: '♥', className: 'bg-red-700 text-white', name: 'hearts' },
  d: { symbol: '♦', className: 'bg-blue-700 text-white', name: 'diamonds' },
  c: { symbol: '♣', className: 'bg-emerald-700 text-white', name: 'clubs' },
}

const RANK: Record<string, string> = { T: '10' }

/** Four-colour deck: suits are distinguishable at a glance, which matters for flush reading. */
export function PlayingCard({ card, size = 'md' }: { card: string; size?: 'sm' | 'md' }) {
  const rank = card[0] ?? '?'
  const suit = SUIT[card[1] ?? ''] ?? SUIT.s!
  return (
    <div
      role="img"
      aria-label={`${RANK[rank] ?? rank} of ${suit.name}`}
      className={cn(
        'flex flex-col items-center justify-center rounded-md font-semibold shadow-sm ring-1 ring-black/20 select-none',
        size === 'md' ? 'h-14 w-10 text-lg' : 'h-11 w-8 text-sm',
        suit.className,
      )}
    >
      <span className="leading-none">{RANK[rank] ?? rank}</span>
      <span className="leading-none">{suit.symbol}</span>
    </div>
  )
}

export function CardRow({
  cards,
  label,
  size,
}: {
  cards: string[]
  label: string
  size?: 'sm' | 'md'
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex gap-1" aria-label={label}>
        {cards.map((c) => (
          <PlayingCard key={c} card={c} size={size} />
        ))}
      </div>
      <span className="text-muted-foreground text-[10px] tracking-wider uppercase">{label}</span>
    </div>
  )
}
