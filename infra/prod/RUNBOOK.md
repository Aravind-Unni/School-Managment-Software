# Deploying the school platform — runbook

One school per server. Everything runs in Docker Compose: PostgreSQL, Redis,
MinIO (private file storage), the API, a background worker, a scheduler, the
web frontend behind nginx, Caddy for HTTPS, and a nightly backup job.

## 1. What you need

- A Linux VPS (2 vCPU / 4 GB RAM is comfortable for ~4,000 students) with
  Docker Engine and the Compose plugin.
- A domain name, e.g. `school.example.in`, with an A record pointing at the
  server. Ports **80 and 443** must be open (Caddy gets the TLS certificate).
- This repository on the server.

## 2. Configure

```bash
cd /path/to/repo
python3 infra/prod/make-env.py school.example.in      # writes infra/prod/.env with fresh secrets
```

This prints the first owner's login and password. Keep `infra/prod/.env`
safe and **never regenerate it on a live install**. If
`TOTP_ENCRYPTION_KEY` changes, every authenticator enrolment stops working.

Edit **`infra/prod/school.toml`** with the school's name, academic year and
terms, and any sections that differ from the default of one section "A" per
standard. Every other option (subjects per standard, bell schedule, working
days, grading bands, attendance warning level, library limits, roles and their
permissions) has a default in `backend/config/school_defaults.toml`. Copy any
section you want to change into `school.toml`.

Check the file before starting:

```bash
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env run --rm api \
  python backend/manage.py install_school --check
```

## 3. Start

```bash
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env up -d --build
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env ps
curl -fsS https://school.example.in/healthz
```

On every start the API applies database migrations and then `school.toml`.
Both are idempotent.

## 4. First owner

```bash
set -a; . infra/prod/.env; set +a
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env exec api \
  python backend/manage.py bootstrap_owner --login "$OWNER_LOGIN" --password "$OWNER_PASSWORD"
```

Open `https://school.example.in/login`, sign in, set up the authenticator app,
and save the recovery codes. Then change the password under
**Admin → Security**.

## 5. Setting up the school (in the browser)

The owner's home page lists these steps in order:

1. **School setup**: check the name, year, classes and subjects.
2. **Staff & teaching**: add each teacher, give them a login (a temporary
   password is shown once; print or copy it), and assign what they teach.
   A teacher only sees attendance and mark sheets for classes they teach.
3. **Admit a student**: student, class and parent in one form, with an
   optional parent login. Use "Existing parent" for siblings. For many
   students at once, use **Imports**.
4. **Timetable**: a draft with the bell schedule already exists. Fill it in
   and publish it.
5. **Fees**: set up fee heads and plans.
6. **Accounts & logins**: review who can sign in, reset forgotten passwords,
   and deactivate people who leave.

Staff roles require 2FA. Parents and students sign in with a password only;
this is configurable per role in `school.toml`.

## 6. Changing configuration later

Edit `infra/prod/school.toml`, then:

```bash
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env restart api
```

Roles listed in the file are managed by the file. Change their permissions
there, not in the product.

## 7. Backups and restore

The `backup` service writes `db-<time>.dump` (PostgreSQL) and
`objects-<time>.tar.gz` (uploaded files) into the `school_prod_backups`
volume at start-up and nightly at `BACKUP_HOUR_UTC` (default 20:00 UTC,
which is 01:30 IST), keeping `BACKUP_KEEP_DAYS` days.

**Copy backups off the server** (a backup on the same disk is not a backup):

```bash
docker run --rm -v school_prod_school_prod_backups:/b -v "$PWD":/out alpine \
  sh -c 'cp /b/$(ls -t /b | grep ^db- | head -1) /out/'
```

Schedule that (plus the newest `objects-*.tar.gz`) with cron to another
machine or cloud storage.

Restore drill (do this once before go-live, and record how long it took):

```bash
C="docker compose -f infra/prod/compose.yml --env-file infra/prod/.env"
$C stop api worker scheduler
$C exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
$C exec -T postgres pg_restore -U school -d school_prod --no-owner < db-<time>.dump
# files: untar objects-<time>.tar.gz into the school_prod_objects volume
$C start api worker scheduler
```

## 8. Updating the software

```bash
git pull
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env up -d --build
```

Take a backup first (`$C restart backup` runs one immediately).

## 9. Health

- `https://<domain>/healthz` is public and minimal.
- `/readyz` (full readiness, including configuration) is only reachable from
  the server itself:
  `docker compose ... exec web wget -qO- http://127.0.0.1/readyz`.
- Logs: `docker compose ... logs -f api worker scheduler`.

## 10. Known limitations

- SMS is not connected. Notices are in-app only until an SMS provider is
  contracted and configured.
- Printed report cards are English-only PDFs. The PDF writer embeds no
  Malayalam font, so Malayalam report cards need a font bundle added first.
- Alumni data exports are accepted but not yet delivered as files.
