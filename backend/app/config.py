import os
import pathlib

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

MIGRATIONS_DIR = ROOT / "backend" / "migrations"
DB_NAME = os.environ.get("DB_NAME", "thisissus")
TEST_DB_NAME = os.environ.get("DB_TEST_NAME", "thisissus_test")


def dsn(db_name: str = DB_NAME) -> str:
    e = os.environ
    return f"postgresql://{e['DB_USER']}:{e['DB_PASSWORD']}@{e['DB_HOST']}:{e['DB_PORT']}/{db_name}"
