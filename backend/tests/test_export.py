from app.export import export_all, safe_name
from tests.helpers import in_space, signup
from tests.media_fixtures import jpeg_bytes


async def setup(client, conn, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.EXPORT_DIR", tmp_path)
    await in_space(client, conn, "Ana")
    await conn.execute("UPDATE spaces SET name = 'Midva' WHERE name = 'Us'")
    date_id = (await client.post("/api/dates", json={"title": "Piknik: Bled/Jezero", "starts_at": "2026-06-14T12:00:00Z"})).json()["id"]
    first = jpeg_bytes(noise=True, w=64, h=64)
    m1 = (await client.post(f"/api/dates/{date_id}/photos", files={"file": ("a.jpg", first, "image/jpeg")})).json()["id"]
    await client.patch(f"/api/dates/{date_id}/photos/{m1}", json={"caption": "Sončni zahod"})
    m2 = (await client.post(f"/api/dates/{date_id}/photos", files={"file": ("b.jpg", jpeg_bytes(), "image/jpeg")})).json()["id"]
    await client.delete(f"/api/dates/{date_id}/photos/{m2}")  # in trash → not exported
    gone = (await client.post("/api/dates", json={"title": "Izbrisan", "starts_at": "2026-05-01T12:00:00Z"})).json()["id"]
    await client.post(f"/api/dates/{gone}/photos", files={"file": ("c.jpg", jpeg_bytes(), "image/jpeg")})
    await client.delete(f"/api/dates/{gone}")
    recipe_id = (await client.post("/api/recipes", json={"title": "Ramen"})).json()["id"]
    await client.post(f"/api/recipes/{recipe_id}/photos", files={"file": ("r.png", jpeg_bytes(), "image/jpeg")})
    return first


def files(root):
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file())


async def test_export_writes_a_browsable_tree_of_originals(client, conn, tmp_path, monkeypatch):
    first = await setup(client, conn, tmp_path, monkeypatch)

    result = await export_all(conn, {})

    assert files(tmp_path) == ["Midva/recepti/Ramen/01.jpg", "Midva/zmenki/2026/06/2026-06-14 Piknik_ Bled_Jezero/01-Sončni zahod.jpg"]
    assert (tmp_path / "Midva/zmenki/2026/06/2026-06-14 Piknik_ Bled_Jezero/01-Sončni zahod.jpg").read_bytes() == first
    assert result == {"files": 2, "written": 2}


async def test_rerun_skips_existing_files(client, conn, tmp_path, monkeypatch):
    await setup(client, conn, tmp_path, monkeypatch)
    await export_all(conn, {})

    again = await export_all(conn, {})

    assert again == {"files": 2, "written": 0}


def test_safe_names():
    assert safe_name('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"
    assert safe_name("  CON  ") == "_CON"
    assert safe_name("x" * 200) == "x" * 80
    assert safe_name("") == "_"


async def test_admin_starts_export_and_sees_status(client, conn, tmp_path, monkeypatch):
    await setup(client, conn, tmp_path, monkeypatch)
    await signup(client, conn, "Admin", roles=["admin"])

    assert (await client.post("/api/admin/export")).status_code == 200
    assert await conn.fetchval("SELECT count(*) FROM jobs WHERE kind = 'media.export' AND done_at IS NULL") == 1
    assert (await client.post("/api/admin/export")).status_code == 200  # no duplicate while one is queued
    assert await conn.fetchval("SELECT count(*) FROM jobs WHERE kind = 'media.export' AND done_at IS NULL") == 1
    status = (await client.get("/api/admin/export")).json()
    assert status["queued"] is True and status["dir"] == str(tmp_path)


async def test_only_admins_export(client, conn):
    await in_space(client, conn)

    assert (await client.post("/api/admin/export")).status_code == 403
