"""Trash: soft-deleted items (deleted_at) can be restored for 30 days, then the daily trash.purge job removes them for good.

Each trashable type registers SQL here; ideas and recipes add entries in their slices.
"""
import asyncpg

TRASH_DAYS = 30


async def _purge_date(conn: asyncpg.Connection, date_id: int) -> None:
    # Originals attached to the date (derivatives + chunks follow via ON DELETE CASCADE), then the date itself.
    await conn.execute("DELETE FROM media WHERE id IN (SELECT media_id FROM date_media WHERE date_id = $1)", date_id)
    await conn.execute("DELETE FROM dates WHERE id = $1", date_id)


async def _purge_media(conn: asyncpg.Connection, media_id: int) -> None:
    await conn.execute("DELETE FROM media WHERE id = $1", media_id)


TYPES = {
    "idea": {
        "list": "SELECT 'idea' AS type, id, title AS label, deleted_at FROM ideas WHERE space_id = $1 AND deleted_at IS NOT NULL",
        "space": "SELECT space_id FROM ideas WHERE id = $1 AND deleted_at IS NOT NULL",
        "restore": "UPDATE ideas SET deleted_at = NULL WHERE id = $1",
        "expired": "SELECT id FROM ideas WHERE deleted_at < now() - make_interval(days => $1)",
        "purge": lambda conn, idea_id: conn.execute("DELETE FROM ideas WHERE id = $1", idea_id),
    },
    "date": {
        "list": "SELECT 'date' AS type, id, title AS label, deleted_at FROM dates WHERE space_id = $1 AND deleted_at IS NOT NULL",
        "space": "SELECT space_id FROM dates WHERE id = $1 AND deleted_at IS NOT NULL",
        "restore": "UPDATE dates SET deleted_at = NULL WHERE id = $1",
        "expired": "SELECT id FROM dates WHERE deleted_at < now() - make_interval(days => $1)",
        "purge": _purge_date,
    },
    "photo": {  # photos/videos removed from a date that itself still exists
        "list": """SELECT 'photo' AS type, m.id, d.title AS label, m.deleted_at FROM media m
                   JOIN date_media dm ON dm.media_id = m.id JOIN dates d ON d.id = dm.date_id
                   WHERE m.space_id = $1 AND m.variant = 'original' AND m.deleted_at IS NOT NULL AND d.deleted_at IS NULL""",
        "space": "SELECT space_id FROM media WHERE id = $1 AND variant = 'original' AND deleted_at IS NOT NULL",
        "restore": "UPDATE media SET deleted_at = NULL WHERE id = $1",
        "expired": "SELECT id FROM media WHERE variant = 'original' AND deleted_at < now() - make_interval(days => $1)",
        "purge": _purge_media,
    },
}


async def list_trash(conn: asyncpg.Connection, space_id: int) -> list[dict]:
    sql = " UNION ALL ".join(t["list"] for t in TYPES.values())
    return [dict(r) for r in await conn.fetch(f"SELECT * FROM ({sql}) t ORDER BY deleted_at DESC", space_id)]


async def item_space(conn: asyncpg.Connection, kind: str, item_id: int) -> int | None:
    return await conn.fetchval(TYPES[kind]["space"], item_id) if kind in TYPES else None


async def restore(conn: asyncpg.Connection, kind: str, item_id: int) -> None:
    await conn.execute(TYPES[kind]["restore"], item_id)


async def purge(conn: asyncpg.Connection, kind: str, item_id: int) -> None:
    await TYPES[kind]["purge"](conn, item_id)


async def purge_expired(conn: asyncpg.Connection, payload: dict) -> None:
    """Worker job trash.purge (daily)."""
    for kind, spec in TYPES.items():
        for row in await conn.fetch(spec["expired"], TRASH_DAYS):
            await spec["purge"](conn, row["id"])
