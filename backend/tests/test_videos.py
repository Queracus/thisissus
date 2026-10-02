import json
import shutil
import subprocess

import pytest

from tests.helpers import in_space
from tests.media_fixtures import open_image
from tests.test_media import drain_jobs, upload

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
PICNIC = {"title": "Picnic", "starts_at": "2026-06-14T12:00:00+02:00"}


def make_clip(tmp_path, codec="libx265") -> bytes:
    """1-second test clip with a GPS location tag, like an iPhone .mov."""
    out = tmp_path / "clip.mov"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=1",
                    "-f", "lavfi", "-i", "sine=duration=1", "-c:v", codec, "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-metadata", "location=+46.3700+014.1000/", "-shortest", str(out)], check=True)
    return out.read_bytes()


def probe(data: bytes, tmp_path) -> dict:
    f = tmp_path / "probe.mp4"
    f.write_bytes(data)
    res = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(f)], capture_output=True, check=True)
    return json.loads(res.stdout)


async def date_id_in_space(client, conn):
    await in_space(client, conn)
    return (await client.post("/api/dates", json=PICNIC)).json()["id"]


async def test_video_is_converted_to_h264_mp4_with_poster(client, conn, tmp_path):
    date_id = await date_id_in_space(client, conn)
    res = await upload(client, date_id, make_clip(tmp_path), "IMG_0002.MOV", "video/quicktime")
    assert res.status_code == 200, res.text
    assert res.json()["kind"] == "video"

    await drain_jobs(conn)

    media_id = res.json()["id"]
    video = (await client.get(f"/api/dates/{date_id}")).json()["photos"][0]
    assert (video["kind"], video["status"], video["width"], video["height"]) == ("video", "ready", 640, 360)
    assert 0.9 < video["duration_s"] < 1.2
    info = probe((await client.get(f"/api/media/{media_id}/mp4")).content, tmp_path)
    assert info["streams"][0]["codec_name"] == "h264"
    assert open_image((await client.get(f"/api/media/{media_id}/thumb")).content).format == "WEBP"
    assert open_image((await client.get(f"/api/media/{media_id}/poster")).content).format == "WEBP"


async def test_converted_video_has_no_location_metadata(client, conn, tmp_path):
    date_id = await date_id_in_space(client, conn)
    media_id = (await upload(client, date_id, make_clip(tmp_path), "clip.mov", "video/quicktime")).json()["id"]

    await drain_jobs(conn)

    tags = probe((await client.get(f"/api/media/{media_id}/mp4")).content, tmp_path)["format"].get("tags", {})
    assert not any("location" in k.lower() for k in tags), tags


async def test_mp4_variant_supports_seeking(client, conn, tmp_path):
    date_id = await date_id_in_space(client, conn)
    media_id = (await upload(client, date_id, make_clip(tmp_path), "clip.mov", "video/quicktime")).json()["id"]
    await drain_jobs(conn)

    res = await client.get(f"/api/media/{media_id}/mp4", headers={"Range": "bytes=100-199"})

    assert res.status_code == 206 and len(res.content) == 100
    assert res.headers["content-type"] == "video/mp4"


async def test_video_size_limit_is_separate_from_photos(client, conn, tmp_path, monkeypatch):
    date_id = await date_id_in_space(client, conn)
    monkeypatch.setattr("app.media.store.VIDEO_MAX_BYTES", 1000)

    res = await upload(client, date_id, make_clip(tmp_path), "clip.mov", "video/quicktime")

    assert (res.status_code, res.json()) == (413, {"code": "media.too_large"})
