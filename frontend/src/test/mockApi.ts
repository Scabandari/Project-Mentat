import { vi } from 'vitest'

export type Handler = (body: unknown) => unknown
export type Routes = Record<string, Handler | unknown>

/** Mock global fetch by "METHOD /path" keys. Handlers may be values or functions of the body. */
export function mockApi(routes: Routes) {
  const calls: { key: string; body: unknown }[] = []
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const req = input instanceof Request ? input : new Request(String(input))
    const key = `${req.method} ${new URL(req.url).pathname}`
    const text = await req.text()
    const body = text ? (JSON.parse(text) as unknown) : undefined
    calls.push({ key, body })
    if (!(key in routes)) {
      return new Response(JSON.stringify({ error: { code: 'http_404', message: key } }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    const route = routes[key]
    const data = typeof route === 'function' ? (route as Handler)(body) : route
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  return { spy, calls }
}
