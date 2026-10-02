import os
import pathlib

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

MIGRATIONS_DIR = ROOT / "backend" / "migrations"
DB_NAME = os.environ.get("DB_NAME", "thisissus")
TEST_DB_NAME = os.environ.get("DB_TEST_NAME", "thisissus_test")

# Passkeys are bound to RP_ID + ORIGIN: localhost in dev, the .si domain in prod.
RP_ID = os.environ.get("RP_ID", "localhost")
RP_NAME = "Thisissus"
ORIGIN = os.environ.get("ORIGIN", "http://localhost:5173")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

# Web push (generate with: python -m app.cli vapid-keys)
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@localhost")


def dsn(db_name: str = DB_NAME) -> str:
    e = os.environ
    return f"postgresql://{e['DB_USER']}:{e['DB_PASSWORD']}@{e['DB_HOST']}:{e['DB_PORT']}/{db_name}"
