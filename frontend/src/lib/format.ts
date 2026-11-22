import type { Scene } from '@/api'

export function formatMoney(x: number, format: Scene['money_format']) {
  return format === 'live' ? `$${x.toLocaleString('en-US')}` : `${x}bb`
}
