# Rollback Runbook

Triage matrix for production incidents and the cheapest way out of each.

## Decide first: code or data?

- **Code regression** (5xx spike, wrong behavior, no DB schema change): roll back the deployment.
- **Bad migration on live data** (constraint violation, accidental column drop): roll back the schema, or restore from snapshot.
- **Config-only** (wrong CORS origin, wrong cookie domain, leaked secret): patch the env var and redeploy.

## Code regression — redeploy a previous build

Fastest path. Railway keeps the artifacts of recent deploys.

1. Railway dashboard → `api` service → Deployments.
2. Find the last green deploy before the regression.
3. Click "Redeploy" — the previous container image is reused; no rebuild needed.
4. Confirm `/v1/health` returns 200 and run the smoke test from [deploy.md](./deploy.md).

If the regression is in `web` only, redeploy that service alone.

## Bad migration — reversible

If the failing migration has a working `downgrade()`:

```bash
railway run --service api uv run alembic downgrade -1
```

Then "Redeploy" the prior `api` deployment so the code matches the schema again. Investigate locally with a Postgres dump before re-rolling forward.

## Bad migration — irreversible (data loss)

If the migration dropped/truncated data or has no downgrade:

1. Put the `api` service into maintenance (Railway → service → Pause).
2. Restore Postgres from the most recent snapshot (Railway dashboard → Postgres plugin → Backups → Restore).
3. Note the snapshot timestamp — any writes after that moment are gone.
4. Bring the prior `api` build back via "Redeploy."
5. Unpause and run the smoke test.
6. Write a postmortem in `docs/adr/` documenting which migration mis-fired and what guard prevents it next time.

> Test the restore path **before** an incident. Once per quarter: spin up a scratch Railway project, restore yesterday's snapshot, confirm `alembic upgrade head` is a no-op.

## Cookies / CORS broken in prod

Symptom: signup works, page refresh logs the user out, or browser console shows blocked cross-origin requests.

1. Check `FRONTEND_URLS` on the `api` service — must list the exact web origin, no trailing slash.
2. Check `VITE_API_BASE_URL` on the `web` service — `https://<api-domain>/v1`, not the proxy path `/v1`.
3. Confirm `api` and `web` share an eTLD+1; the refresh cookie is `SameSite=Strict` and won't cross sites.
4. Patch the env var, redeploy the affected service.

## Compromised secret

JWT or refresh secret leaked:

1. Generate replacements: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
2. Set `JWT_SECRET` and `JWT_REFRESH_SECRET` on the `api` service (rotate both together).
3. Redeploy `api`. **Every active session is invalidated** — users must log in again. Acceptable for a leak; communicate beforehand if scheduled.

## Account lockout review

A burst of `423 ACCOUNT_LOCKED` errors in the logs usually indicates either a brute-force attempt or a broken client. To unlock a single demo account during the assessment review:

```bash
railway run --service api uv run python -c "
import asyncio
from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.models.user import User

async def unlock():
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User).where(User.email == 'demo@ethara.example')
            .values(failed_login_count=0, locked_until=None)
        )
        await db.commit()

asyncio.run(unlock())
"
```

## Communications

- Internal channel: Railway → Notifications routes deploy + health alerts.
- External users (assessment reviewer): drop a note in the PR thread referencing the affected commit and ETA.
