import httpx


async def test_health_ok(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


async def test_unknown_route_uses_error_envelope(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "http_404"


async def test_openapi_exposes_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/openapi.json")
    assert r.status_code == 200
    assert "/api/v1/health" in r.json()["paths"]
