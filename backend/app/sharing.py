"""Read-only sharing rules (used by app.policy-style checks and the shares router).

A share grants READ access to one item, or to every item of one type in a space (section), for one account
(or a secret link, #31). Shares never grant writes: every mutating endpoint keeps checking space membership only.
"""
import asyncpg

TABLES = {"date": "dates", "idea": "ideas", "recipe": "recipes"}
LIVE = "s.revoked_at IS NULL AND (s.expires_at IS NULL OR s.expires_at > now())"


async def entity_space(conn: asyncpg.Connection, entity_type: str, entity_id: int) -> int | None:
    if entity_type not in TABLES:
        return None
    return await conn.fetchval(f"SELECT space_id FROM {TABLES[entity_type]} WHERE id = $1 AND deleted_at IS NULL", entity_id)


def _grants(target_sql: str) -> str:
    """Active shares ($1 = target, $2 = type, $3 = item id, $4 = item's space) that cover the item."""
    return f"""SELECT s.* FROM shares s WHERE {LIVE} AND {target_sql} AND s.entity_type = $2
               AND ((s.scope = 'item' AND s.entity_id = $3) OR (s.scope = 'section' AND s.space_id = $4))
               ORDER BY s.scope = 'item' DESC, s.id LIMIT 1"""


async def user_grant(conn: asyncpg.Connection, user_id: int, entity_type: str, entity_id: int) -> asyncpg.Record | None:
    space_id = await entity_space(conn, entity_type, entity_id)
    if space_id is None:
        return None
    return await conn.fetchrow(_grants("s.target_user_id = $1"), user_id, entity_type, entity_id, space_id)


async def link_share(conn: asyncpg.Connection, token: str) -> asyncpg.Record | None:
    """The live share behind a secret link (only the token's sha256 is stored)."""
    from app.auth.tokens import hash_token
    return await conn.fetchrow(f"SELECT s.*, sp.name AS space_name FROM shares s JOIN spaces sp ON sp.id = s.space_id "
                               f"WHERE s.token_hash = $1 AND {LIVE}", hash_token(token))


async def link_covers(conn: asyncpg.Connection, share: asyncpg.Record, entity_type: str, entity_id: int) -> bool:
    if share["entity_type"] != entity_type:
        return False
    if share["scope"] == "item":
        return share["entity_id"] == entity_id and await entity_space(conn, entity_type, entity_id) is not None
    return await entity_space(conn, entity_type, entity_id) == share["space_id"]


async def link_can_see_media(conn: asyncpg.Connection, share: asyncpg.Record, media_id: int) -> bool:
    for entity_type, entity_id in await media_owners(conn, media_id):
        if await link_covers(conn, share, entity_type, entity_id):
            return True
    return False


async def media_owners(conn: asyncpg.Connection, media_id: int) -> list[tuple[str, int]]:
    rows = await conn.fetch("""SELECT 'date' AS t, date_id AS id FROM date_media WHERE media_id = $1
                               UNION ALL SELECT 'recipe', recipe_id FROM recipe_media WHERE media_id = $1""", media_id)
    return [(r["t"], r["id"]) for r in rows]


async def user_can_see_media(conn: asyncpg.Connection, user_id: int, media_id: int) -> bool:
    for entity_type, entity_id in await media_owners(conn, media_id):
        if await user_grant(conn, user_id, entity_type, entity_id):
            return True
    return False


async def contacts(conn: asyncpg.Connection, user_id: int) -> list[dict]:
    """People I share at least one space with: the only ones I can share to (no user discovery)."""
    rows = await conn.fetch(
        """SELECT DISTINCT u.id, u.display_name FROM space_members mine JOIN space_members other ON other.space_id = mine.space_id
           JOIN users u ON u.id = other.user_id WHERE mine.user_id = $1 AND u.id <> $1 AND u.disabled_at IS NULL ORDER BY u.display_name""",
        user_id)
    return [dict(r) for r in rows]


async def shared_with(conn: asyncpg.Connection, user_id: int) -> list[dict]:
    """Every item shared with me (item shares + expanded section shares), newest share first."""
    parts = [f"""SELECT DISTINCT ON (e.id) '{t}' AS type, e.id, e.title, u.display_name AS shared_by_name, sp.name AS space_name, s.created_at
                 FROM shares s JOIN {table} e ON e.deleted_at IS NULL
                      AND ((s.scope = 'item' AND e.id = s.entity_id) OR (s.scope = 'section' AND e.space_id = s.space_id))
                 JOIN spaces sp ON sp.id = s.space_id LEFT JOIN users u ON u.id = s.created_by
                 WHERE {LIVE} AND s.target_user_id = $1 AND s.entity_type = '{t}'
                 ORDER BY e.id, s.scope = 'item' DESC"""
             for t, table in TABLES.items()]
    rows = await conn.fetch(f"SELECT * FROM ({' UNION ALL '.join(f'({p})' for p in parts)}) x ORDER BY created_at DESC, type, id", user_id)
    return [dict(r) for r in rows]
