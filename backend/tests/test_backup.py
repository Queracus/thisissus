import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app import config
from tests.helpers import in_space, signup

SCRIPT = Path(__file__).resolve().parents[2] / "ops" / "backup.sh"


def find_bash() -> str | None:
    """Linux: system bash. Windows: Git Bash (System32's bash.exe is WSL and can't see Windows paths/tools)."""
    if os.name != "nt":
        return shutil.which("bash")
    git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"
    return str(git_bash) if git_bash.exists() else None


BASH = find_bash()
needs_tools = pytest.mark.skipif(not (BASH and shutil.which("pg_dump")), reason="bash + pg_dump needed")


def run_backup(backup_dir, **env):
    # Forward slashes: Git Bash on Windows needs them, Linux doesn't mind.
    return subprocess.run([BASH, SCRIPT.as_posix()], capture_output=True, text=True, timeout=120,
                          env={**os.environ, "BACKUP_DIR": Path(backup_dir).as_posix(), "DB_NAME": config.TEST_DB_NAME, **env})


def dumps(backup_dir):
    return sorted(p.name for p in Path(backup_dir).glob("thisissus-*.dump"))


@needs_tools
def test_backup_keeps_the_newest_two_and_writes_status(tmp_path, test_db):
    for _ in range(3):
        res = run_backup(tmp_path)
        assert res.returncode == 0, res.stderr
        time.sleep(1.1)  # dump names have one-second resolution

    status = json.loads((tmp_path / "backup-status.json").read_text())
    assert len(dumps(tmp_path)) == 2
    assert status["ok"] is True and status["file"] == dumps(tmp_path)[-1] and status["size"] > 0
    assert 0 <= status["disk_used_pct"] <= 100


@needs_tools
def test_failed_backup_leaves_previous_dumps_intact(tmp_path, test_db):
    assert run_backup(tmp_path).returncode == 0
    before = dumps(tmp_path)

    res = run_backup(tmp_path, DB_NAME="no_such_database")

    assert res.returncode == 1
    assert dumps(tmp_path) == before
    assert not list(tmp_path.glob("*.tmp"))
    assert json.loads((tmp_path / "backup-status.json").read_text())["ok"] is False


async def test_admin_sees_backup_status_and_warnings(client, conn, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.BACKUP_DIR", str(tmp_path))
    await in_space(client, conn)
    await signup(client, conn, "Admin", roles=["admin"])
    old = (datetime.now(UTC) - timedelta(hours=30)).isoformat().replace("+00:00", "Z")
    (tmp_path / "backup-status.json").write_text(json.dumps({"time": old, "ok": True, "file": "x.dump", "size": 10, "disk_used_pct": 85}))

    status = (await client.get("/api/admin/backup-status")).json()

    assert status["ok"] is True and status["file"] == "x.dump"
    assert sorted(status["warnings"]) == ["backup.disk_almost_full", "backup.stale"]


async def test_missing_status_is_a_warning_not_an_error(client, conn, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.BACKUP_DIR", str(tmp_path / "nothing-here"))
    await signup(client, conn, "Admin", roles=["admin"])

    assert (await client.get("/api/admin/backup-status")).json() == {"ok": None, "warnings": ["backup.never_ran"]}


async def test_only_admins_see_backup_status(client, conn):
    await in_space(client, conn)

    assert (await client.get("/api/admin/backup-status")).status_code == 403
