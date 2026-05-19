# Ethara.AI — Team Task Manager

A production-grade full-stack team task management application built with FastAPI, React, and PostgreSQL.

## Live demo

| Surface | URL                                  |
| ------- | ------------------------------------ |
| Web app | https://app.ethara.example           |
| API     | https://api.ethara.example/v1        |
| Health  | https://api.ethara.example/v1/health |

> Replace the placeholders above with the Railway domains issued after the first deploy. Update `FRONTEND_URLS` (api) and `VITE_API_BASE_URL` (web) to match.

**Demo credentials** — seeded by `apps/api/app/scripts/seed.py`:

| Email                 | Password       |
| --------------------- | -------------- |
| `demo@ethara.example` | `DemoPass123!` |

## Stack

- **Backend:** Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL
- **Frontend:** React 19 · Vite · TypeScript · TailwindCSS · TanStack Query
- **Infra:** Docker · Railway · GitHub Actions

## Quick Start

```bash
# Prerequisites: Node 22, pnpm, uv, Docker Desktop
git clone https://github.com/deepd9137/Ethara.AI.git
cd Ethara.AI
make bootstrap   # installs deps, starts postgres, runs migrations
make api         # terminal 1 — http://localhost:8000
make web         # terminal 2 — http://localhost:5173
```

## Commands

| Command          | Description                |
| ---------------- | -------------------------- |
| `make bootstrap` | One-shot setup after clone |
| `make up`        | Start Postgres             |
| `make api`       | Run API dev server         |
| `make web`       | Run web dev server         |
| `make migrate`   | Apply DB migrations        |
| `make test`      | Run all tests              |
| `make lint`      | Lint all code              |
| `make fmt`       | Format all code            |
| `make seed`      | Seed demo user + project   |

## Deployment

Railway via push-to-main. Service config is checked in:

- `apps/api/railway.toml` + `apps/api/nixpacks.toml` — backend (uv + alembic + uvicorn)
- `apps/web/railway.toml` — frontend (pnpm build, served with `serve`)

Step-by-step in [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md). Incident response in [`docs/runbooks/rollback.md`](docs/runbooks/rollback.md).

## Docs

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — full engineering handbook
- [`SPECIFICATION.md`](SPECIFICATION.md) — product requirements
- [`docs/runbooks/`](docs/runbooks/) — deploy + rollback procedures
