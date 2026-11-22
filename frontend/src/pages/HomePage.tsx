import { useGetHealthQuery } from '@/api/generated'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function HomePage() {
  const { data, isLoading, isError, refetch } = useGetHealthQuery()
  const healthy = data?.status === 'ok'

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-6 p-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Mentat</h1>
        <p className="text-muted-foreground">Poker math, at the speed of thought.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>System status</CardTitle>
          <CardDescription>API and database connectivity</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div className="flex items-center gap-2" data-testid="health">
            <span
              className={cn(
                'size-2.5 rounded-full',
                isLoading ? 'bg-muted-foreground' : healthy ? 'bg-success' : 'bg-destructive',
              )}
            />
            <span>
              {isLoading
                ? 'Checking…'
                : isError || !data
                  ? 'API unreachable'
                  : `API ${data.status} · DB ${data.db} · v${data.version}`}
            </span>
          </div>
          <Button variant="outline" size="sm" onClick={() => void refetch()}>
            Recheck
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}
