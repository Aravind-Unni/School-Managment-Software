# VPS install runbook — one school, browser via nginx

## Preconditions

- A VPS with Docker Engine + Compose plugin
- A DNS A/AAAA record pointing at the VPS
- Filled `infra/prod/.env` (never commit it)
- TLS: terminate with Certbot/Caddy in front of `HOST_HTTP_PORT`, or extend nginx for 443

## Bring up

```bash
cd /path/to/repo
cp infra/prod/.env.example infra/prod/.env
# edit infra/prod/.env — every blank is required
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env up -d --build
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env ps
curl -fsS http://127.0.0.1:${HOST_HTTP_PORT:-80}/healthz
```

## First owner (production has no seed)

```bash
docker compose -f infra/prod/compose.yml --env-file infra/prod/.env \
  exec -e OWNER_LOGIN -e OWNER_PASSWORD -e OWNER_DISPLAY_NAME \
  api python backend/manage.py bootstrap_owner
```

Then open `https://<ALLOWED_HOST>/login` and enrol 2FA for the owner.

## Data

- Do **not** run `scripts/dev.py seed` against production.
- Import students/staff via M13 exchange / registry UI, or enter via the product.
- Never invent plausible school data in fixtures for a live campus.

## Backups

- Postgres volume `school_prod_pg` — nightly `pg_dump` off-box
- Object volume `school_prod_objects` — mirror the private bucket off-box
- Record RPO/RTO after the first restore drill (C02 restore suite)

## Release acceptance

After school staff smoke (admin, teacher, guardian) on the live hostname, ops +
school contact sign `docs/integration/release-checklist.md`. Only then set
`RELEASE_ACCEPTED` in `docs/integration/release-manifest.json`.
