import * as React from 'react'

import { cn } from '@/lib/utils'

function Progress({
  value,
  className,
  indicatorClassName,
  ...props
}: React.ComponentProps<'div'> & { value: number; indicatorClassName?: string }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={cn('bg-secondary relative h-1.5 w-full overflow-hidden rounded-full', className)}
      {...props}
    >
      <div
        className={cn('bg-primary h-full transition-[width] duration-300', indicatorClassName)}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export { Progress }
