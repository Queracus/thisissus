from tests.helpers import signup


async def test_new_users_default_to_slovenian(client, conn):
    await signup(client, conn, "Ana")

    assert (await client.get("/api/auth/me")).json()["locale"] == "sl"


async def test_user_switches_to_english(client, conn):
    await signup(client, conn, "Ana")

    assert (await client.put("/api/me/locale", json={"locale": "en"})).status_code == 200

    assert (await client.get("/api/auth/me")).json()["locale"] == "en"


async def test_unsupported_locale_is_rejected(client, conn):
    await signup(client, conn, "Ana")

    res = await client.put("/api/me/locale", json={"locale": "de"})

    assert res.json() == {"code": "validation.invalid", "fields": ["locale"]}
