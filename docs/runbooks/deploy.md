# Deploy Runbook

How to deploy the Team Task Manager to Railway from a clean checkout. Targets the assessment reviewer; one-time setup, then push-to-deploy.

## Prereqs

- Railway account with billing enabled (free hobby tier is fine).
- `railway` CLI ≥ 3 installed and logged in (`railway login`).
- GitHub repo connected (so push-to-main triggers a deploy).

## One-time setup

```bash
# From repo root
railway init                          # create a new project
railway add --plugin postgresql       # provision Postgres
```

Create two Railway services from the GitHub repo:

| Service | Root directory | Auto-detected config                                                           |
| ------- | -------------- | ------------------------------------------------------------------------------ |
| `api`   | `apps/api`     | `railway.toml` + `nixpacks.toml`                                               |
| `web`   | (repo root)    | `apps/web/railway.toml` (set "Config-as-Code Path" to `apps/web/railway.toml`) |

The web service builds from the repo root because pnpm needs the workspace `pnpm-lock.yaml`.

### API service variables

Set in the Railway dashboard or via CLI:

```bash
railway variables --service api \
  --set "ENVIRONMENT=production" \
  --set "APP_VERSION=1.0.0" \
  --set "DATABASE_URL=\${{Postgres.DATABASE_URL_ASYNCPG}}" \
  --set "JWT_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  --set "JWT_REFRESH_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  --set "FRONTEND_URLS=https://<your-web-domain>" \
  --set "LOG_LEVEL=INFO" \
  --set "DOCS_ENABLED=false" \
  --set "SENTRY_DSN=https://...@sentry.io/..."
```

`Postgres.DATABASE_URL_ASYNCPG` is a Railway computed variable — define it as a reference on the Postgres plugin with value `${{DATABASE_URL}}` and replace `postgresql://` with `postgresql+asyncpg://`. Alternatively set `DATABASE_URL` directly with the right prefix.

### Web service variables

```bash
railway variables --service web \
  --set "VITE_API_BASE_URL=https://<your-api-domain>/v1" \
  --set "VITE_ENVIRONMENT=production" \
  --set "VITE_SENTRY_DSN=https://...@sentry.io/..." \
  --set "VITE_COMMIT_SHA=\${{RAILWAY_GIT_COMMIT_SHA}}"
```

> Vite inlines `VITE_*` vars at **build time**. Changing one requires a redeploy, not just a restart.

### Cookie domain

The API issues the refresh cookie on path `/v1/auth` with `SameSite=Strict`. The `api` and `web` services must share an eTLD+1 (e.g. `api.example.com` + `app.example.com`) for the cookie to flow back. In Railway, configure custom domains accordingly — `*.up.railway.app` subdomains don't share an eTLD+1 across services.

## Deploying

`main` is the deploy branch. Push or merge into `main`; Railway's GitHub integration builds and rolls out both services automatically.

```bash
git push origin main
railway logs --service api    # follow deploy
railway logs --service web
```

## Migrations

`alembic upgrade head` is the first step in the `api` service's start command (`railway.toml`). The container does not start serving traffic until migrations complete; a failing migration halts the deploy and the previous version keeps serving.

To run a migration outside a deploy (e.g. a data backfill):

```bash
railway run --service api uv run alembic upgrade head
```

## Seeding the demo account

```bash
railway run --service api uv run python -m app.scripts.seed
```

Creates `demo@ethara.example` / `DemoPass123!` plus a sample project with three tasks. Idempotent — safe to re-run.

## Post-deploy smoke test

1. `curl https://<api-domain>/v1/health` → `{"status":"ok","db":"ok",...}` in < 5 s.
2. Open `https://<web-domain>` — login page renders.
3. Sign up a fresh account → create a project → create a task → mark it done.
4. Hard-reload the page; you should stay logged in (refresh-cookie boot path).
5. Trigger a test error (DELETE a non-existent task) → confirm structured JSON error envelope.
6. Sentry → confirm test error appears within ~30 s.

## Monitoring

- **Logs:** Railway dashboard → `api` service → Logs tab. All entries are JSON; `request_id` correlates frontend errors to backend traces.
- **Health:** Railway runs the configured `healthcheckPath` automatically; alerts fire on failures.
- **Alerts:** configure Railway → Notifications → 5xx rate > 1% over 5 min → email/Slack.
- **Backups:** Railway Postgres takes daily snapshots automatically. Test restores quarterly (see [rollback.md](./rollback.md)).
