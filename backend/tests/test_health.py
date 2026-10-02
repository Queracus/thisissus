async def test_health_reports_api_and_db_ok(client):
    res = await client.get("/api/health")

    assert res.status_code == 200
    assert res.json() == {"ok": True, "db": True}
