# Ethara.AI — Team Task Manager

A production-grade full-stack team task management application built with FastAPI, React, and PostgreSQL.

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

See `ARCHITECTURE.md` for the full engineering handbook and `SPECIFICATION.md` for product requirements.
