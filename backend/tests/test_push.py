import json

from app import push
from app.notify import notify
from tests.helpers import in_space, login, signup

SUB = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "BPk", "auth": "xyz"}}


class FakeResponse:
    def __init__(self, status):
        self.status_code = status


def capture(monkeypatch, status_for=lambda endpoint: 201):
    sent = []

    def fake_webpush(subscription_info, data, **kw):
        sent.append((subscription_info["endpoint"], json.loads(data)))
        status = status_for(subscription_info["endpoint"])
        if status >= 400:
            raise push.WebPushException("gone", response=FakeResponse(status))
    monkeypatch.setattr(push, "webpush", fake_webpush)
    return sent


async def couple(client, conn):
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    return ana_id, bor_id, ana, bor


async def test_subscribe_and_unsubscribe(client, conn):
    _, bor_id, _, _ = await couple(client, conn)

    assert (await client.post("/api/push/subscriptions", json=SUB)).status_code == 200
    assert await conn.fetchval("SELECT user_id FROM push_subscriptions WHERE endpoint = $1", SUB["endpoint"]) == bor_id
    await client.request("DELETE", "/api/push/subscriptions", json={"endpoint": SUB["endpoint"]})
    assert await conn.fetchval("SELECT count(*) FROM push_subscriptions") == 0


async def test_public_key_is_served(client, conn, monkeypatch):
    await couple(client, conn)
    monkeypatch.setattr("app.config.VAPID_PUBLIC_KEY", "PUBKEY")

    assert (await client.get("/api/push/public-key")).json() == {"key": "PUBKEY"}


async def test_push_is_sent_in_the_recipients_language(client, conn, monkeypatch):
    ana_id, bor_id, _, _ = await couple(client, conn)
    await client.post("/api/push/subscriptions", json=SUB)  # Bor's phone
    await conn.execute("UPDATE users SET locale = 'en' WHERE id = $1", bor_id)
    sent = capture(monkeypatch)
    ids = await notify(conn, ana_id, "idea.created", {"idea_id": 5, "title": "Kino"}, [bor_id])

    await push.send(conn, {"notification_ids": ids})

    assert sent == [(SUB["endpoint"], {"title": "Thisissus 💌", "body": "Ana has a new idea: Kino", "url": "/ideas/5"})]


async def test_slovenian_is_the_default(client, conn, monkeypatch):
    ana_id, bor_id, _, _ = await couple(client, conn)
    await client.post("/api/push/subscriptions", json=SUB)
    sent = capture(monkeypatch)

    await push.send(conn, {"notification_ids": await notify(conn, ana_id, "idea.created", {"idea_id": 5, "title": "Kino"}, [bor_id])})

    assert sent[0][1]["body"] == "Ana ima novo idejo: Kino"


async def test_expired_subscription_is_removed(client, conn, monkeypatch):
    ana_id, bor_id, _, _ = await couple(client, conn)
    await client.post("/api/push/subscriptions", json=SUB)
    await client.post("/api/push/subscriptions", json={**SUB, "endpoint": "https://push.example/alive"})
    capture(monkeypatch, status_for=lambda e: 410 if e.endswith("abc") else 201)

    await push.send(conn, {"notification_ids": await notify(conn, ana_id, "idea.created", {"idea_id": 5, "title": "Kino"}, [bor_id])})

    assert [r["endpoint"] for r in await conn.fetch("SELECT endpoint FROM push_subscriptions")] == ["https://push.example/alive"]


async def test_vapid_keys_are_valid_p256(client):
    public, private = push.generate_vapid_keys()

    assert len(push.b64decode(public)) == 65 and push.b64decode(public)[0] == 4
    assert len(push.b64decode(private)) == 32
