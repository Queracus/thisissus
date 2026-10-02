#!/usr/bin/env bash
# Nightly full backup: pg_dump → verify → keep the newest $KEEP dumps → status JSON for the admin panel.
#
#   BACKUP_DIR=/mnt/usb/thisissus ops/backup.sh
#
# Connection: DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME from the environment or the repo's .env.
# A failed run never touches existing dumps; it only writes ok=false into the status file and exits 1.
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
# .env only fills in what the environment doesn't already set (environment wins).
if [ -f "$here/../.env" ]; then
  while IFS='=' read -r key value; do
    case "$key" in ''|\#*) continue ;; esac
    [ -z "${!key+set}" ] && export "$key=${value%$'\r'}"
  done < "$here/../.env"
fi

BACKUP_DIR="${BACKUP_DIR:?set BACKUP_DIR, e.g. /mnt/usb/thisissus}"
KEEP="${KEEP:-2}"
export PGHOST="${DB_HOST:-localhost}" PGPORT="${DB_PORT:-5432}" PGUSER="${DB_USER:-thisissus}" PGPASSWORD="${DB_PASSWORD:-}"
DB="${DB_NAME:-thisissus}"
status="$BACKUP_DIR/backup-status.json"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

used_pct() { df -P "$BACKUP_DIR" | awk 'NR==2 { gsub("%", "", $5); print $5 }'; }

fail() {
  printf '{"time": "%s", "ok": false, "error": "%s", "disk_used_pct": %s}\n' "$(now)" "$1" "$(used_pct || echo null)" > "$status"
  rm -f "$tmp"
  echo "backup failed: $1" >&2
  exit 1
}

mkdir -p "$BACKUP_DIR" || { echo "cannot create $BACKUP_DIR" >&2; exit 1; }
name="thisissus-$(date -u +%Y%m%d-%H%M%S).dump"
tmp="$BACKUP_DIR/$name.tmp"

pg_dump -Fc -d "$DB" -f "$tmp" 2>"$BACKUP_DIR/last-error.log" || fail "pg_dump failed (see last-error.log)"
pg_restore --list "$tmp" >/dev/null 2>>"$BACKUP_DIR/last-error.log" || fail "dump did not verify"
mv "$tmp" "$BACKUP_DIR/$name" || fail "could not rename dump"

# Rotate only after the new dump is safely in place.
ls -1t "$BACKUP_DIR"/thisissus-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do rm -f "$old"; done

size=$(wc -c < "$BACKUP_DIR/$name" | tr -d ' ')
printf '{"time": "%s", "ok": true, "file": "%s", "size": %s, "disk_used_pct": %s}\n' "$(now)" "$name" "$size" "$(used_pct)" > "$status"
rm -f "$BACKUP_DIR/last-error.log"
echo "backup ok: $name ($size bytes)"
