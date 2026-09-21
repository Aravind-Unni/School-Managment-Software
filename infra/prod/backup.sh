#!/bin/sh
# Nightly backup loop: a compressed pg_dump plus a tarball of the private
# object store, kept for BACKUP_KEEP_DAYS days in /backups. Runs once at
# start-up (so a fresh install has a backup immediately) and then daily at
# BACKUP_HOUR_UTC (20 = 01:30 IST... 20:00 UTC is 01:30 IST the next day).
# A failed run is logged and retried the next night; the loop never exits.
set -u
mkdir -p /backups

run_backup() {
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  echo "backup: starting ${stamp}"
  if pg_dump --format=custom --no-owner --file="/backups/db-${stamp}.dump.partial" \
    && mv "/backups/db-${stamp}.dump.partial" "/backups/db-${stamp}.dump" \
    && tar -C /objects -czf "/backups/objects-${stamp}.tar.gz.partial" . \
    && mv "/backups/objects-${stamp}.tar.gz.partial" "/backups/objects-${stamp}.tar.gz"; then
    find /backups -name 'db-*.dump' -mtime +"${BACKUP_KEEP_DAYS}" -delete
    find /backups -name 'objects-*.tar.gz' -mtime +"${BACKUP_KEEP_DAYS}" -delete
    find /backups -name '*.partial' -delete
    echo "backup: finished ${stamp}"
  else
    echo "backup: FAILED ${stamp}"
  fi
}

seconds_until_next_run() {
  now=$(date -u +%s)
  into_day=$((now % 86400))
  target=$((BACKUP_HOUR_UTC * 3600))
  wait=$(((target - into_day + 86400) % 86400))
  [ "$wait" -eq 0 ] && wait=86400
  echo "$wait"
}

run_backup
while true; do
  sleep "$(seconds_until_next_run)"
  run_backup
done
