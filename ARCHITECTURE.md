# ARCHITECTURE.md — Team Task Manager

> **Type:** Engineering execution handbook
> **Status:** Implementation-ready · Solo-developer optimized
> **Companion document:** [`SPECIFICATION.md`](./SPECIFICATION.md) — read it first for product / API / DB contracts
> **Repo:** https://github.com/deepd9137/Ethara.AI.git
> **Deploy target:** Railway
> **Version:** 1.0.0

This document is the **operating manual** for building, shipping, and maintaining the Team Task Manager. Where the spec answers _what & why_, this answers _how, in what order, with which commands, with which commits_.

---

## Table of Contents

1. [Engineering Vision](#1-engineering-vision)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Monorepo / Project Structure](#3-monorepo--project-structure)
4. [Complete Environment Setup Guide (Zero → Running)](#4-complete-environment-setup-guide-zero--running)
5. [Git Workflow & Branching Strategy](#5-git-workflow--branching-strategy)
6. [Development Roadmap Overview](#6-development-roadmap-overview)
7. [Phase 0 — Repository Bootstrap](#7-phase-0--repository-bootstrap)
8. [Phase 1 — Backend Foundation](#8-phase-1--backend-foundation)
9. [Phase 2 — Authentication System](#9-phase-2--authentication-system)
10. [Phase 3 — Project Management Module](#10-phase-3--project-management-module)
11. [Phase 4 — Task Management Module](#11-phase-4--task-management-module)
12. [Phase 5 — Frontend Foundation](#12-phase-5--frontend-foundation)
13. [Phase 6 — Dashboard & Analytics](#13-phase-6--dashboard--analytics)
14. [Phase 7 — UI Polish & UX](#14-phase-7--ui-polish--ux)
15. [Phase 8 — Testing & QA](#15-phase-8--testing--qa)
16. [Phase 9 — Deployment & Production](#16-phase-9--deployment--production)
17. [CI/CD Pipeline](#17-cicd-pipeline)
18. [Database Architecture & Migration Strategy](#18-database-architecture--migration-strategy)
19. [API Architecture Standards](#19-api-architecture-standards)
20. [Frontend Architecture Standards](#20-frontend-architecture-standards)
21. [Security Architecture](#21-security-architecture)
22. [Error Handling & Logging Strategy](#22-error-handling--logging-strategy)
23. [Performance Optimization Plan](#23-performance-optimization-plan)
24. [Edge Cases & Failure Planning](#24-edge-cases--failure-planning)
25. [Local Development Workflow](#25-local-development-workflow)
26. [Commands Reference](#26-commands-reference)
27. [Engineering Rules & Code Standards](#27-engineering-rules--code-standards)
28. [Acceptance Criteria Per Phase](#28-acceptance-criteria-per-phase)
29. [Debugging & Troubleshooting Guide](#29-debugging--troubleshooting-guide)
30. [Final Production Checklist](#30-final-production-checklist)

---

## 1. Engineering Vision

### 1.1 Philosophy

> **Ship a small, correct, observable system. Earn complexity.**

Five operating principles drive every decision in this document:

| Principle                      | What it means in practice                                                                                      |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **Production-first**           | Every feature is built behind real validation, real auth, real logging from day 1. No "we'll harden it later". |
| **API-first contracts**        | OpenAPI is the single source of truth. Frontend writes against the spec, not the implementation.               |
| **Vertical slices**            | Each phase ships an end-to-end thin slice (DB → API → UI). Avoid horizontal layers built in isolation.         |
| **Tight feedback loops**       | Pre-commit hooks + CI < 5 min + fast tests. The build tells the truth in seconds, not days.                    |
| **Trunk-based, small commits** | `main` is always deployable. Branches live hours, not days. Each commit is reversible.                         |

### 1.2 MVP Strategy

- **Scope discipline**: implement only what `SPECIFICATION.md` §3 lists. Notifications, comments, attachments are explicitly post-MVP.
- **Two-roles RBAC**: Admin + Member, project-scoped — nothing more (cf. spec §4).
- **Email/password auth only** for MVP. SSO is a post-MVP phase.
- **One deployment target**: Railway. No multi-cloud hedging on day 1.

### 1.3 Scalability Goals

- Stateless API → horizontal scale via Railway replicas (no sticky sessions).
- DB-bound: every hot query has an index documented in spec §9.3.
- Cache layer (Redis) wired but **optional** — the app must run without it.

### 1.4 Maintainability Goals

- One feature ≈ one folder (feature-based on both ends).
- No magic globals. Settings via `pydantic-settings`; runtime config explicit.
- ADRs (`docs/adr/`) capture any non-obvious decision.
- Coverage gate ≥ 80% backend; UI critical paths covered by Playwright.

### 1.5 Clean Architecture Philosophy

Backend:

```
HTTP (FastAPI router)  ──►  Service (business rules)  ──►  Repository (DB I/O)  ──►  ORM
```

Hard rules:

- **Routers** validate input shape and authorization; they do **not** contain business logic.
- **Services** own business rules, FSMs, cross-entity invariants.
- **Repositories** own SQL/ORM; they return models or DTOs, never raw rows.
- **No raw SQL** outside repositories.

Frontend:

```
Page  ──►  Container/hook  ──►  API function  ──►  Axios client
              │
              └──►  Component (presentational)
```

Hard rules:

- Presentational components take props, render JSX, no fetching.
- Hooks own server state via TanStack Query.
- Forms: Hook Form + Zod resolver, period.

### 1.6 Solo-Developer Execution Strategy

- **Daily slice**: ship at least one PR every working day, even if it's small.
- **One branch at a time**: avoid context-switching tax.
- **Stop the line**: if CI fails on `main`, fix is the only acceptable next commit.
- **Demo loop**: after each phase, screenshot or video the working flow before moving on.

### 1.7 Backend Architecture Philosophy

- **Async everywhere**: `AsyncEngine`, `AsyncSession`, `async def` routes, `httpx.AsyncClient` for outbound.
- **Stateless services**: no module-level mutable state; settings/loggers injected via `Depends`.
- **Single transaction per request** (cf. spec §11.4); activity-log writes share that transaction.
- **Explicit error taxonomy**: a `BusinessError(code, status, details)` class maps to the envelope in spec §10.2.

### 1.8 API-First Development

1. Define Pydantic schemas first → OpenAPI auto-generated.
2. Generate TS types from `openapi.json` (script in §17).
3. Frontend implements against the spec; backend cannot break it without a version bump.

---

## 2. System Architecture Overview

> **Full system, request, auth, ER, deploy diagrams are in `SPECIFICATION.md` §8.** This section adds **execution-flow** diagrams the spec doesn't have.

### 2.1 Repo → CI → Deploy Pipeline

```mermaid
flowchart LR
    DEV[Local dev<br/>pre-commit hooks] --> PUSH[git push feature branch]
    PUSH --> PR[Open PR → main]
    PR --> CI[GitHub Actions:<br/>lint · type · test · build]
    CI -->|green| REV[Reviewer / self-review]
    REV --> MERGE[Squash merge → main]
    MERGE --> RW[Railway: detect push]
    RW --> BUILD[Nixpacks build]
    BUILD --> MIG[alembic upgrade head]
    MIG -->|ok| DEPLOY[Replace old deployment]
    MIG -->|fail| HALT[Halt; old version stays]
    DEPLOY --> HC[/health check x3]
    HC -->|ok| LIVE[Live]
    HC -->|fail| AUTO_RB[Auto-rollback]
```

### 2.2 Local Development Loop

```mermaid
flowchart TB
    subgraph "Terminal A: infra"
      PG[(docker compose up postgres redis)]
    end
    subgraph "Terminal B: API"
      API[uvicorn app.main:app --reload<br/>http://localhost:8000]
    end
    subgraph "Terminal C: Web"
      WEB[pnpm dev<br/>http://localhost:5173]
    end
    PG -.-> API
    WEB -- "VITE_API_BASE_URL=/v1 → proxy → 8000" --> API
    DEV[Developer] --> WEB
    DEV --> API
```

### 2.3 Request Lifecycle (concise; full version in spec §8.2)

```mermaid
sequenceDiagram
    Client->>FastAPI: HTTP + Bearer
    FastAPI->>Middleware: request_id, log, rate-limit
    Middleware->>Deps: get_current_user → require_project_*
    Deps->>Service: invoke
    Service->>Repository: queries
    Repository->>PostgreSQL: SQL
    PostgreSQL-->>Repository: rows
    Repository-->>Service: models
    Service-->>FastAPI: DTO
    FastAPI-->>Client: envelope JSON
```

### 2.4 Auth Flow (concise; full version in spec §8.3)

```mermaid
sequenceDiagram
    Client->>API: POST /auth/login
    API-->>Client: 200 {access} + Set-Cookie refresh (HttpOnly)
    Client->>API: GET /resource (Bearer)
    API-->>Client: 401 expired
    Client->>API: POST /auth/refresh (cookie)
    API-->>Client: 200 {access} + new refresh cookie
    Client->>API: retry GET /resource
```

### 2.5 Branching / Release Flow

```mermaid
gitGraph
    commit id: "main: bootstrap"
    branch feat/p1-fastapi
    commit id: "feat: app factory"
    commit id: "feat: health"
    commit id: "test: health"
    checkout main
    merge feat/p1-fastapi tag: "P1 ✓"
    branch feat/p2-auth-signup
    commit id: "feat: signup"
    commit id: "test: signup"
    checkout main
    merge feat/p2-auth-signup
```

---

## 3. Monorepo / Project Structure

### 3.1 Layout

```txt
Ethara.AI/
├── apps/
│   ├── api/                       # FastAPI backend
│   │   ├── app/                   # source (cf. spec §12.6 for full tree)
│   │   ├── tests/
│   │   ├── alembic/
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── ruff.toml
│   │   ├── mypy.ini
│   │   ├── alembic.ini
│   │   ├── Dockerfile             # for local parity / optional
│   │   ├── .env.example
│   │   └── README.md
│   └── web/                       # React frontend
│       ├── src/                   # source (cf. spec §13.2 for full tree)
│       ├── e2e/                   # Playwright tests
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── tailwind.config.ts
│       ├── postcss.config.js
│       ├── eslint.config.js
│       ├── .env.example
│       └── README.md
├── packages/
│   └── shared-types/              # optional: codegen'd from openapi.json
├── docs/
│   ├── adr/                       # Architecture Decision Records
│   ├── runbooks/                  # deploy, rollback, secret-rotation, oncall
│   └── img/                       # screenshots for README
├── scripts/
│   ├── bootstrap.sh               # one-shot dev setup
│   ├── seed.py                    # demo data
│   ├── reset-db.sh
│   ├── generate-openapi.sh
│   └── generate-types.sh          # openapi → TS types
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── e2e.yml
│   │   └── deploy-trigger.yml
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
├── .husky/
│   ├── pre-commit
│   └── commit-msg
├── docker-compose.yml             # postgres + redis for local
├── Makefile                       # ergonomic shortcuts
├── package.json                   # pnpm workspace root
├── pnpm-workspace.yaml
├── .nvmrc
├── .gitignore
├── .editorconfig
├── .prettierrc
├── commitlint.config.js
├── .pre-commit-config.yaml        # python-side hooks (optional)
├── CLAUDE.md
├── SPECIFICATION.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### 3.2 Why Each Folder

| Path                    | Purpose                                                     | CI watches?          |
| ----------------------- | ----------------------------------------------------------- | -------------------- |
| `apps/api`              | Self-contained backend; can deploy independently            | `paths: apps/api/**` |
| `apps/web`              | Self-contained frontend; can deploy independently           | `paths: apps/web/**` |
| `packages/shared-types` | Optional TS types generated from OpenAPI                    | yes if used          |
| `docs/adr`              | Append-only architecture decisions; reviewers must check it | no (docs PR only)    |
| `docs/runbooks`         | Oncall scripts; opened during incidents                     | no                   |
| `scripts/`              | One-shot dev helpers; cross-platform `sh`                   | no                   |
| `.github/workflows`     | CI/CD definitions                                           | meta                 |
| `.husky/`               | Client-side commit gates                                    | meta                 |

### 3.3 Naming Conventions (cross-cutting)

| Element       | Rule                          | Example                                  |
| ------------- | ----------------------------- | ---------------------------------------- |
| Branch        | `<type>/<phase>-<slice>`      | `feat/p2-auth-refresh-rotation`          |
| Commit        | Conventional                  | `feat(auth): rotate refresh on each use` |
| Python module | `snake_case`                  | `task_service.py`                        |
| Python class  | `PascalCase`                  | `TaskService`                            |
| TS component  | `PascalCase` file = component | `TaskCard.tsx`                           |
| TS hook       | `useCamelCase`                | `useProjectTasks.ts`                     |
| Env var       | `UPPER_SNAKE`                 | `JWT_REFRESH_SECRET`                     |
| DB column     | `snake_case`                  | `assignee_id`                            |
| API path      | `/kebab-case`                 | `/projects/{id}/transfer-owner`          |

### 3.4 Shared Configuration Strategy

- **TS**: each app has its own `tsconfig.json` extending a shared base (`tsconfig.base.json` at root if needed).
- **Lint**: ESLint flat config at `apps/web`; ruff at `apps/api`. Root holds Prettier + commitlint + husky.
- **Env**: each app has its own `.env.example`; no shared `.env`.
- **Secrets**: Railway env vars per service; never `.env` in CI.

---

## 4. Complete Environment Setup Guide (Zero → Running)

> **Time to first request: ~25 minutes** on a fresh machine.
> Supported OS: macOS (Apple Silicon + Intel), Linux, WSL2. Native Windows works but Docker is recommended for Postgres.

### 4.1 Prerequisites

Install one toolchain at a time. Verify each before proceeding.

#### macOS

```bash
# Homebrew (if missing)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Core tools
brew install git make
brew install --cask docker            # Docker Desktop (for Postgres)
brew install nvm                      # Node version manager

# Verify
git --version
docker --version
```

#### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y git make curl build-essential

# Docker — follow official install (docker.io OR docker-ce)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

#### Windows

Use WSL2 + Ubuntu and follow the Linux path above.

### 4.2 Node + pnpm

```bash
# Match repo's .nvmrc (created in Phase 0)
nvm install 20
nvm use 20
node --version    # → v20.x

# Activate pnpm via corepack (no global npm install)
corepack enable
corepack prepare pnpm@9 --activate
pnpm --version    # → 9.x
```

`.nvmrc`:

```
20
```

`.tool-versions` (for asdf users; optional):

```
nodejs 20.11.1
python 3.12.4
```

### 4.3 Python via uv

`uv` is a Rust-implemented, drop-in replacement for `pip + virtualenv + pip-tools`. It is **10–100× faster** than pip, produces a deterministic lockfile, and manages Python versions itself.

```bash
# Install uv (one-liner; works on macOS / Linux / WSL)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Re-source shell so uv is on PATH
exec $SHELL -l

# Verify
uv --version

# uv can install Python itself — no need for pyenv
uv python install 3.12
```

**Why uv?**

1. Lockfile (`uv.lock`) guarantees reproducible builds across CI / Railway.
2. Resolves and installs in seconds even for fat deps.
3. Single binary, no global Python pollution.
4. Drop-in: `uv pip install`, `uv run`, `uv add`, `uv sync`.

### 4.4 PostgreSQL (Docker)

Avoid host-level Postgres — Docker Compose keeps dev parity with Railway managed PG.

```bash
# In repo root after clone
docker compose up -d postgres
docker compose ps                     # postgres should be (healthy)
docker compose logs postgres --tail 20
```

Local DSN:

```
postgresql+asyncpg://postgres:postgres@localhost:5432/ttm
```

### 4.5 Clone & Verify Remote

```bash
git clone https://github.com/deepd9137/Ethara.AI.git
cd Ethara.AI

git remote -v
# origin  https://github.com/deepd9137/Ethara.AI.git (fetch)
# origin  https://github.com/deepd9137/Ethara.AI.git (push)

# Configure identity (once per machine)
git config user.name  "Your Name"
git config user.email "you@example.com"

# Optional: signed commits
git config commit.gpgsign true
```

### 4.6 Workspace Install

```bash
# From repo root
pnpm install                          # installs all workspace deps + hooks
```

This will:

- Resolve `pnpm-workspace.yaml` → installs `apps/web` deps.
- Install root devDeps (husky, commitlint, prettier).
- Run `husky install` automatically via the `prepare` script.

### 4.7 Backend Bootstrap

```bash
cd apps/api

uv venv                               # creates .venv with Python 3.12
source .venv/bin/activate             # on Windows: .venv\Scripts\activate
uv sync                               # installs deps from pyproject.toml + uv.lock
```

Copy env:

```bash
cp .env.example .env
# edit DATABASE_URL, JWT_SECRET, JWT_REFRESH_SECRET
```

Generate strong secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4.8 Database Migrations

```bash
# from apps/api with .venv active
alembic upgrade head                  # apply all migrations
```

Optional seed:

```bash
python scripts/seed.py                # demo user, project, tasks
```

### 4.9 Frontend Env

```bash
cd ../web
cp .env.example .env
# VITE_API_BASE_URL=http://localhost:8000/v1
```

### 4.10 Start Dev Servers

Three terminals (or `make dev` to start all):

```bash
# Terminal A — infra
docker compose up postgres            # foreground for log visibility

# Terminal B — backend
cd apps/api && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal C — frontend
cd apps/web && pnpm dev
```

Open:

- Web: http://localhost:5173
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### 4.11 Railway CLI

```bash
# Install
brew install railway                    # macOS
# OR
curl -fsSL https://railway.app/install.sh | sh

railway login                           # opens browser
railway link                            # link this repo to a Railway project
```

### 4.12 Config-File Templates (paste verbatim)

#### `.nvmrc`

```
20
```

#### `.editorconfig`

```ini
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
max_line_length = 100

[*.py]
indent_size = 4
max_line_length = 88

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

#### `.gitignore` (root, abridged)

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
.python-version
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Node
node_modules/
.pnpm-store/
dist/
build/
.vite/
.turbo/

# Env
.env
.env.local
.env.*.local
!.env.example

# OS / IDE
.DS_Store
.idea/
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
!.vscode/launch.json

# Build artifacts
*.log
coverage/
playwright-report/
test-results/

# Railway
.railway/
```

#### `.env.example` (api)

```env
ENVIRONMENT=local
APP_VERSION=0.1.0
GIT_SHA=local
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ttm
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
JWT_SECRET=change-me-to-48-bytes-base64
JWT_REFRESH_SECRET=change-me-to-different-48-bytes-base64
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=1209600
BCRYPT_ROUNDS=12
FRONTEND_URLS=http://localhost:5173
RATE_LIMIT_AUTH_PER_5MIN=10
RATE_LIMIT_USER_PER_MIN=120
LOG_LEVEL=DEBUG
DOCS_ENABLED=true
SENTRY_DSN=
REDIS_URL=
```

#### `.env.example` (web)

```env
VITE_API_BASE_URL=http://localhost:8000/v1
VITE_ENVIRONMENT=local
VITE_SENTRY_DSN=
VITE_COMMIT_SHA=local
```

#### `package.json` (root, workspace)

```json
{
  "name": "ethara-monorepo",
  "private": true,
  "packageManager": "pnpm@9.0.0",
  "engines": { "node": "20" },
  "scripts": {
    "prepare": "husky",
    "dev": "pnpm -r --parallel --filter \"./apps/*\" dev",
    "build": "pnpm -r --filter \"./apps/*\" build",
    "lint": "pnpm -r --filter \"./apps/*\" lint",
    "typecheck": "pnpm -r --filter \"./apps/*\" typecheck",
    "test": "pnpm -r --filter \"./apps/*\" test",
    "format": "prettier --write \"**/*.{ts,tsx,js,jsx,md,json,yml,yaml}\""
  },
  "devDependencies": {
    "@commitlint/cli": "^19.0.0",
    "@commitlint/config-conventional": "^19.0.0",
    "husky": "^9.0.0",
    "lint-staged": "^15.0.0",
    "prettier": "^3.2.0",
    "prettier-plugin-tailwindcss": "^0.5.0"
  },
  "lint-staged": {
    "*.{ts,tsx,js,jsx,json,md,yml,yaml}": ["prettier --write"],
    "apps/web/**/*.{ts,tsx}": ["eslint --fix"],
    "apps/api/**/*.py": ["ruff check --fix", "black"]
  }
}
```

#### `pnpm-workspace.yaml`

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

#### `.prettierrc`

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always",
  "endOfLine": "lf",
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

#### `apps/web/eslint.config.js` (flat config)

```js
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import hooks from "eslint-plugin-react-hooks";
import a11y from "eslint-plugin-jsx-a11y";
import importPlugin from "eslint-plugin-import";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "playwright-report"] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { react, "react-hooks": hooks, "jsx-a11y": a11y, import: importPlugin },
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "react/jsx-no-leaked-render": "error",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "jsx-a11y/anchor-is-valid": "error",
      "import/order": [
        "error",
        {
          groups: ["builtin", "external", "internal", "parent", "sibling", "index"],
          "newlines-between": "always",
          alphabetize: { order: "asc" },
        },
      ],
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: "dangerouslySetInnerHTML is forbidden.",
        },
      ],
    },
    settings: { react: { version: "detect" } },
  },
);
```

#### `commitlint.config.js`

```js
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "chore",
        "ci",
        "build",
        "revert",
      ],
    ],
    "scope-empty": [1, "never"],
    "subject-case": [2, "never", ["upper-case", "pascal-case"]],
    "header-max-length": [2, "always", 100],
  },
};
```

#### `.husky/pre-commit`

```sh
pnpm exec lint-staged
```

#### `.husky/commit-msg`

```sh
pnpm exec commitlint --edit "$1"
```

#### `apps/api/pyproject.toml`

```toml
[project]
name = "ttm-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy>=2.0",
  "asyncpg>=0.29",
  "alembic>=1.13",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "passlib[bcrypt]>=1.7",
  "python-jose[cryptography]>=3.3",
  "python-multipart>=0.0.9",
  "structlog>=24.1",
  "orjson>=3.10",
  "httpx>=0.27",
  "slowapi>=0.1.9",
]

[dependency-groups]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "pytest-cov>=5.0",
  "factory-boy>=3.3",
  "ruff>=0.5",
  "black>=24.4",
  "mypy>=1.10",
  "types-passlib",
  "pip-audit>=2.7",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["app"]

[tool.coverage.report]
fail_under = 80
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]
```

#### `apps/api/ruff.toml`

```toml
line-length = 88
target-version = "py312"
extend-exclude = ["alembic/versions"]

[lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM", "RUF", "ASYNC", "S"]
ignore = ["E501"]  # line length owned by black

[lint.per-file-ignores]
"tests/*" = ["S101", "S106"]
"alembic/env.py" = ["E402"]

[format]
quote-style = "double"
```

#### `apps/api/mypy.ini`

```ini
[mypy]
python_version = 3.12
strict = True
plugins = pydantic.mypy
exclude = (alembic/versions/|\.venv/)
warn_unreachable = True
warn_unused_ignores = True
disallow_untyped_decorators = False

[mypy-tests.*]
disallow_untyped_defs = False

[mypy-passlib.*]
ignore_missing_imports = True
```

#### `apps/api/alembic.ini` (key bits)

```ini
[alembic]
script_location = alembic
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
prepend_sys_path = .
timezone = UTC

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console
```

#### `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ttm
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    profiles: ["optional"]

volumes:
  pgdata:
```

#### `Makefile`

```makefile
.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN{FS=":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## One-shot dev setup
	corepack enable
	pnpm install
	cd apps/api && uv venv && uv sync
	cp -n apps/api/.env.example apps/api/.env || true
	cp -n apps/web/.env.example apps/web/.env || true
	docker compose up -d postgres
	cd apps/api && .venv/bin/alembic upgrade head

up: ## Start postgres
	docker compose up -d postgres

down: ## Stop postgres
	docker compose down

api: ## Run api
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000

web: ## Run web
	cd apps/web && pnpm dev

dev: ## Run api + web (requires tmux or run separately)
	@echo "Run 'make api' and 'make web' in separate terminals"

migrate: ## Apply migrations
	cd apps/api && .venv/bin/alembic upgrade head

migration: ## Create migration: make migration name="add users"
	cd apps/api && .venv/bin/alembic revision --autogenerate -m "$(name)"

seed: ## Seed demo data
	cd apps/api && .venv/bin/python ../../scripts/seed.py

test: ## Run all tests
	cd apps/api && .venv/bin/pytest
	cd apps/web && pnpm test --run

fmt: ## Format
	cd apps/api && .venv/bin/black . && .venv/bin/ruff check . --fix
	pnpm format

lint: ## Lint
	cd apps/api && .venv/bin/ruff check . && .venv/bin/black --check . && .venv/bin/mypy .
	cd apps/web && pnpm lint && pnpm typecheck

reset-db: ## Drop and recreate database
	docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS ttm;"
	docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE ttm;"
	$(MAKE) migrate

openapi: ## Export OpenAPI spec
	cd apps/api && .venv/bin/python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > openapi.json

.PHONY: help bootstrap up down api web dev migrate migration seed test fmt lint reset-db openapi
```

---

## 5. Git Workflow & Branching Strategy

### 5.1 Branch Model — Trunk-Based

- `main` — the only long-lived branch. Always green, always deployable.
- Feature branches — short-lived (≤ 24 h ideal, ≤ 3 days max).
- No `develop`, no `release/*` branches. Releases are Railway deploys triggered by `main`.

### 5.2 Branch Naming

```
<type>/p<phase>-<short-kebab-summary>
```

| Type       | Use                           |
| ---------- | ----------------------------- |
| `feat`     | New functionality             |
| `fix`      | Bug fix                       |
| `refactor` | Non-functional code change    |
| `chore`    | Tooling, deps, build, CI      |
| `docs`     | Docs only                     |
| `test`     | Adding/refactoring tests only |
| `perf`     | Performance change            |

Examples:

```
feat/p2-auth-refresh-rotation
fix/p4-task-fsm-reopen
refactor/p3-extract-base-repo
chore/p0-husky-setup
docs/adr-0002-pagination
```

### 5.3 Conventional Commits

```
<type>(<scope>): <imperative subject>

[optional body explaining WHY]

[optional footers: Refs #123, BREAKING CHANGE: ...]
```

Examples:

```
feat(auth): rotate refresh token on each /auth/refresh call
fix(tasks): reject assignee not in project_members
refactor(repositories): extract BaseRepo[T] generic
test(projects): cover last-admin demotion edge case
chore(deps): bump fastapi 0.115.0 → 0.115.4
ci(workflows): cache uv installs between jobs
```

### 5.4 Commit Cadence

- **Aim for one commit per logical step**: failing test, passing test, refactor.
- **Squash before PR if commits are messy WIP.**
- Never combine unrelated changes in a single commit.
- A 30-line commit is easier to review and revert than a 300-line one. Default to small.

### 5.5 Rebase vs Merge

- **Local feature work**: rebase onto `main` to keep linear history.
- **PR → main**: **squash merge only** (configured in repo settings). Squash commit message must be the conventional-commit title.
- **Never** rebase published branches once someone else has pulled them.

### 5.6 PR Standards

`.github/pull_request_template.md`:

```markdown
## Why

<one-paragraph problem statement>

## What

- bullet 1
- bullet 2

## How to test

1. step
2. step
3. step

## Screenshots / videos

<for UI changes>

## Linked spec / ADR

- spec §...
- ADR-0003

## Checklist

- [ ] Tests added / updated
- [ ] `make lint` green locally
- [ ] `make test` green locally
- [ ] Migrations included if schema changed
- [ ] Env vars added to `.env.example` if introduced
- [ ] No `console.log` / `print`
- [ ] No unused imports / dead code
- [ ] Breaking changes flagged
```

### 5.7 PR Hygiene Rules

- ≤ 400 changed lines preferred.
- 1 reviewer (self if solo); no unresolved comments at merge.
- CI green is non-negotiable.
- No force-push to `main` ever.
- Stale branches deleted post-merge (GitHub auto-delete on merge).

### 5.8 Hotfix Flow

```bash
git checkout main && git pull
git checkout -b fix/hotfix-<bug>
# minimal change + test
git push -u origin HEAD
gh pr create --title "fix(area): hotfix description" --base main
# Merge → Railway auto-deploys
```

---

## 6. Development Roadmap Overview

### 6.1 Phase Summary

| #         | Phase               | Slice                                           |   Est. Hours | Depends on | Risk                             |
| --------- | ------------------- | ----------------------------------------------- | -----------: | ---------- | -------------------------------- |
| 0         | Repo bootstrap      | tooling, hooks, CI skeleton                     |          6–8 | —          | Low                              |
| 1         | Backend foundation  | app factory, DB, health, logging                |         8–10 | 0          | Low                              |
| 2         | Authentication      | signup/login/refresh/logout + RBAC deps         |        12–16 | 1          | Med — token rotation correctness |
| 3         | Project module      | Project + ProjectMember + ActivityLog wiring    |        12–14 | 2          | Med — RBAC + 404/403 discipline  |
| 4         | Task module         | Task CRUD, FSM, filters, optimistic concurrency |        12–14 | 3          | Med — FSM edge cases             |
| 5         | Frontend foundation | Vite, router, query, auth pages, axios refresh  |        14–18 | 2 (API)    | Med — refresh token race         |
| 6         | Dashboard           | aggregations, my-tasks, recent-activity         |          6–8 | 4 + 5      | Low                              |
| 7         | UI polish           | a11y, mobile, empty/error states, toasts        |         8–10 | 6          | Low                              |
| 8         | Testing & QA        | coverage gates, Playwright golden paths         |        10–12 | 7          | Med — flaky E2E                  |
| 9         | Deployment          | Railway, env, migrations on deploy, monitoring  |         8–10 | 8          | High — first deploy gotchas      |
| **Total** |                     |                                                 | **96–120 h** |            |                                  |

### 6.2 Critical Path

```mermaid
flowchart LR
    P0[Phase 0<br/>Bootstrap] --> P1[Phase 1<br/>Backend]
    P1 --> P2[Phase 2<br/>Auth]
    P2 --> P3[Phase 3<br/>Projects]
    P3 --> P4[Phase 4<br/>Tasks]
    P2 --> P5[Phase 5<br/>Frontend]
    P4 --> P6[Phase 6<br/>Dashboard]
    P5 --> P6
    P6 --> P7[Phase 7<br/>Polish]
    P7 --> P8[Phase 8<br/>Testing]
    P8 --> P9[Phase 9<br/>Deploy]
```

> **Optimization note:** Phase 5 can start _immediately after Phase 2_ in parallel with Phase 3/4 if mocked API contracts are used. For a strict solo developer, prefer sequential to avoid context switching.

### 6.3 Priority Matrix

| Priority                               | Phases     |
| -------------------------------------- | ---------- |
| **Critical** (blocks everything)       | 0, 1, 2    |
| **High** (core feature set)            | 3, 4, 5, 6 |
| **Medium** (production-quality polish) | 7, 8       |
| **Critical for launch**                | 9          |

### 6.4 One-Time Branch Setup

Run this **once** immediately after the initial commit lands on `main`. It pre-creates every phase branch so you never branch manually — just `git checkout <branch>` when starting a phase.

```bash
# Run from repo root, on main, after the initial commit exists
git checkout main

git checkout -b chore/p0-bootstrap  && git checkout main
git checkout -b feat/p1-backend-foundation && git checkout main
git checkout -b feat/p2-auth          && git checkout main
git checkout -b feat/p3-projects      && git checkout main
git checkout -b feat/p4-tasks         && git checkout main
git checkout -b feat/p5-frontend      && git checkout main
git checkout -b feat/p6-dashboard     && git checkout main
git checkout -b feat/p7-ui-polish     && git checkout main
git checkout -b feat/p8-testing       && git checkout main
git checkout -b chore/p9-deploy       && git checkout main

# Push all branches to GitHub in one shot
git push origin --all

# Verify
git branch -a
```

**Rules:**

- All branches diverge from `main` at the initial commit — they will be rebased onto `main` just before you start working on them, picking up all previous merged work.
- Never commit directly to `main`. Each phase goes through its branch → PR → squash merge.
- When starting a phase: `git checkout <branch> && git rebase main` to get the latest.

---

## 7. Phase 0 — Repository Bootstrap

**Goal:** Empty repo → fully linted, hooked, CI-gated monorepo.

**Branch:** `chore/p0-bootstrap`

**Prereqs:** Section 4 prerequisites installed.

### 7.1 Tasks

1. Initialize pnpm workspace and root configs.
2. Move `pyproject.toml` from root → `apps/api/`.
3. Add Husky + commitlint + lint-staged.
4. Add `.editorconfig`, `.gitignore`, `.prettierrc`, `.nvmrc`.
5. Add `docker-compose.yml` for Postgres.
6. Add `Makefile` and `scripts/bootstrap.sh`.
7. Scaffold `apps/api/` skeleton (empty `app/` folder with `__init__.py` + `main.py` stub).
8. Scaffold `apps/web/` via `pnpm create vite@latest web -- --template react-ts`.
9. Add baseline ESLint, Prettier, Tailwind config.
10. Add `.github/workflows/ci.yml` skeleton (lint + typecheck only).
11. Open PR; ensure CI passes.

### 7.2 Commands (key sequence)

```bash
git checkout -b chore/p0-bootstrap

# Move root pyproject into apps/api
mkdir -p apps/api/app apps/web
git mv pyproject.toml main.py apps/api/ || true
echo "*.pyc" >> apps/api/.gitignore

# Workspace
echo '{"name":"ethara-monorepo","private":true,"packageManager":"pnpm@9.0.0"}' > package.json
cat > pnpm-workspace.yaml <<EOF
packages:
  - "apps/*"
  - "packages/*"
EOF

# Frontend scaffold (from apps/)
cd apps && pnpm create vite@latest web -- --template react-ts && cd ..

# Tailwind
cd apps/web
pnpm add -D tailwindcss postcss autoprefixer
pnpm dlx tailwindcss init -p
cd ../..

# Root devDeps
pnpm add -D -w prettier prettier-plugin-tailwindcss husky lint-staged \
  @commitlint/cli @commitlint/config-conventional

pnpm exec husky init
echo "pnpm exec lint-staged" > .husky/pre-commit
echo "pnpm exec commitlint --edit \$1" > .husky/commit-msg
chmod +x .husky/*

# Configs (paste from §4.12)
# ...

# Verify
pnpm install
pnpm exec prettier --check .
```

### 7.3 Commit Sequence

| #   | Type  | Message                                             |
| --- | ----- | --------------------------------------------------- |
| 1   | chore | `chore(repo): scaffold pnpm workspace`              |
| 2   | chore | `chore(repo): move pyproject to apps/api`           |
| 3   | chore | `chore(web): scaffold vite + react + ts`            |
| 4   | chore | `chore(web): configure tailwindcss`                 |
| 5   | chore | `chore(repo): add prettier + editorconfig + nvmrc`  |
| 6   | chore | `chore(repo): add husky + commitlint + lint-staged` |
| 7   | chore | `chore(repo): add docker-compose for postgres`      |
| 8   | chore | `chore(repo): add Makefile shortcuts`               |
| 9   | ci    | `ci(workflows): add lint + typecheck workflow`      |
| 10  | docs  | `docs(readme): add bootstrap instructions`          |

### 7.4 Acceptance Criteria

- [ ] `git clone … && make bootstrap` succeeds on a fresh machine.
- [ ] `pnpm exec prettier --check .` passes.
- [ ] `pnpm typecheck` passes (empty TS project still has tsc).
- [ ] Committing with an invalid message is **rejected** by commitlint.
- [ ] CI on this PR is green.
- [ ] `make help` prints the menu.

### 7.5 Risks & Mitigations

| Risk                                                       | Mitigation                                                                     |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Workspace pollution (frontend touches root `node_modules`) | Use `pnpm` (content-addressed); root `package.json` declares only dev tooling. |
| Husky hooks not running for fresh clones                   | Use `prepare` script + document in README.                                     |
| Windows line-endings                                       | `.gitattributes` with `* text=auto eol=lf`.                                    |

### 7.6 Rollback

```bash
git checkout main
git branch -D chore/p0-bootstrap
```

Repo state remains as it was post-`uv init`. No infra side-effects.

---

## 8. Phase 1 — Backend Foundation

**Goal:** A FastAPI app that boots, connects to PostgreSQL, responds to `/health`, and ships structured logs.

**Branch:** `feat/p1-backend-foundation`

**Prereqs:** Phase 0.

### 8.1 Tasks

1. Create app factory `app/main.py` with `create_app() → FastAPI`.
2. Wire `Settings` (`pydantic-settings`) reading `.env`.
3. Add `db/session.py` with `AsyncEngine` + `AsyncSessionLocal`.
4. Add `db/base.py` with `DeclarativeBase` + `TimestampMixin` + `SoftDeleteMixin`.
5. Add structlog config with JSON renderer in prod, console in dev.
6. Add `RequestIDMiddleware`, `LoggingMiddleware`, `ExceptionToProblemMiddleware`.
7. Add global exception handlers (BusinessError, ValidationError, fallback).
8. Add `app/api/routes/health.py` returning `{status, db, version, commit}`.
9. Initialize Alembic with async env.py.
10. Create first migration (`0001_initial_schema.py`) — empty for now.
11. Add pytest scaffolding (`conftest.py`, sample test).
12. Add `Dockerfile` (optional for local parity).

### 8.2 Key Implementation Sketches

**`app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware import RequestIDMiddleware, LoggingMiddleware
from app.middleware.exceptions import install_exception_handlers

def create_app() -> FastAPI:
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield  # startup/teardown hooks here

    app = FastAPI(
        title="Team Task Manager",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_URLS,
        allow_credentials=True,
        allow_methods=["GET","POST","PATCH","PUT","DELETE","OPTIONS"],
        allow_headers=["Authorization","Content-Type","If-Match","Idempotency-Key","X-Request-Id"],
        expose_headers=["X-Request-Id"],
    )
    install_exception_handlers(app)
    app.include_router(api_router, prefix="/v1")
    return app

app = create_app()
```

**`app/core/config.py`**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENVIRONMENT: str = "local"
    APP_VERSION: str = "0.1.0"
    GIT_SHA: str = "local"

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ACCESS_TTL_SECONDS: int = 900
    JWT_REFRESH_TTL_SECONDS: int = 1_209_600
    BCRYPT_ROUNDS: int = 12

    FRONTEND_URLS: list[str] = Field(default_factory=list)
    LOG_LEVEL: str = "INFO"
    DOCS_ENABLED: bool = False
    SENTRY_DSN: str = ""

settings = Settings()  # raises ValidationError at import if vars missing
```

**`app/db/session.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

### 8.3 Commit Sequence

| #   | Type  | Message                                                      |
| --- | ----- | ------------------------------------------------------------ |
| 1   | chore | `chore(api): add app/ package scaffolding`                   |
| 2   | feat  | `feat(api): add Settings via pydantic-settings`              |
| 3   | feat  | `feat(api): configure structlog with json/console renderers` |
| 4   | feat  | `feat(api): wire AsyncEngine + AsyncSessionLocal`            |
| 5   | feat  | `feat(api): add Base + TimestampMixin + SoftDeleteMixin`     |
| 6   | feat  | `feat(api): add RequestIDMiddleware`                         |
| 7   | feat  | `feat(api): add LoggingMiddleware`                           |
| 8   | feat  | `feat(api): install global exception handlers`               |
| 9   | feat  | `feat(api): add /health endpoint with DB ping`               |
| 10  | feat  | `feat(api): initialize Alembic with async env`               |
| 11  | feat  | `feat(api): create initial empty migration`                  |
| 12  | test  | `test(health): cover ok and db-down paths`                   |
| 13  | ci    | `ci(workflows): add backend lint + test job`                 |

### 8.4 Acceptance Criteria

- [ ] `uvicorn app.main:app --reload` boots without error.
- [ ] `curl localhost:8000/v1/health` → 200 `{status: ok, db: ok, ...}`.
- [ ] `pytest` runs and passes the health test.
- [ ] `ruff check . && black --check . && mypy .` all clean.
- [ ] `alembic upgrade head` succeeds.
- [ ] Logs contain `request_id` on every line.
- [ ] CI green.

### 8.5 Risks & Mitigations

| Risk                                           | Mitigation                                                       |
| ---------------------------------------------- | ---------------------------------------------------------------- |
| `MissingGreenlet` from sync-style DB calls     | Always `await` async session methods; mypy `strict` flags this.  |
| Forgot to load `.env`                          | `Settings()` raises at import — fail fast.                       |
| Alembic autogenerate empty for first migration | Empty is correct here — models added in Phase 2+.                |
| structlog config not applied                   | Call `configure_logging()` **before** `FastAPI()` instantiation. |

### 8.6 Rollback

```bash
git reset --hard main      # if local
# or revert PR via GitHub UI
```

No DB state created yet; nothing to clean up.

---

## 9. Phase 2 — Authentication System

**Goal:** End-to-end signup → login → access protected endpoint → refresh → logout, with refresh-rotation and reuse-detection.

**Branch:** `feat/p2-auth`

**Prereqs:** Phase 1.

### 9.1 Tasks

1. Add `User` model + Alembic migration.
2. Add `RefreshToken` model + migration.
3. Add `password.py` with bcrypt hash/verify.
4. Add `tokens.py` with JWT encode/decode + jti generation.
5. Add `auth_service.py` (signup, authenticate, issue_tokens, rotate_refresh, revoke_family).
6. Add `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")`.
7. Add `get_current_user` dependency.
8. Add `routes/auth.py` with signup/login/refresh/logout/me/change-password.
9. Add rate limiting via `slowapi`.
10. Add tests covering golden + reuse-detection + lockout paths.

### 9.2 Token Rotation Flow (key correctness)

```python
async def rotate_refresh(token_str: str, db: AsyncSession) -> tuple[str, str]:
    claims = decode_refresh(token_str)             # raises if signature/exp bad
    record = await refresh_repo.get_by_jti(db, claims["jti"])
    if record is None:
        raise BusinessError("REFRESH_EXPIRED", status=401)
    if record.used_at is not None:
        # reuse → revoke entire family
        await refresh_repo.revoke_family(db, record.family_id)
        raise BusinessError("REFRESH_REUSED", status=401)
    record.used_at = utc_now()
    new_refresh = await refresh_repo.issue(db, user_id=record.user_id,
                                            family_id=record.family_id)
    new_access = encode_access(record.user_id)
    return new_access, new_refresh
```

### 9.3 Commit Sequence

| #   | Type | Message                                                                |
| --- | ---- | ---------------------------------------------------------------------- |
| 1   | feat | `feat(db): add User model and migration`                               |
| 2   | feat | `feat(db): add RefreshToken model and migration`                       |
| 3   | feat | `feat(auth): add bcrypt password hashing utilities`                    |
| 4   | feat | `feat(auth): add JWT encode/decode with jti claim`                     |
| 5   | feat | `feat(auth): add auth_service with signup/login`                       |
| 6   | feat | `feat(auth): implement refresh rotation with reuse detection`          |
| 7   | feat | `feat(auth): add OAuth2PasswordBearer + get_current_user dep`          |
| 8   | feat | `feat(auth): add /v1/auth routes (signup, login, refresh, logout, me)` |
| 9   | feat | `feat(auth): rate-limit /v1/auth/* via slowapi`                        |
| 10  | feat | `feat(auth): add /v1/auth/change-password`                             |
| 11  | test | `test(auth): cover signup happy path + EMAIL_TAKEN`                    |
| 12  | test | `test(auth): cover login + INVALID_CREDENTIALS + lockout`              |
| 13  | test | `test(auth): cover refresh rotation + reuse-detection family revoke`   |
| 14  | test | `test(auth): assert no PII appears in logs`                            |

### 9.4 Acceptance Criteria

- [ ] `POST /v1/auth/signup` creates user + returns tokens.
- [ ] `POST /v1/auth/login` with wrong password returns generic `INVALID_CREDENTIALS`.
- [ ] After login, `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict`.
- [ ] Replaying a used refresh token revokes the family + returns 401.
- [ ] 10 failed logins in 5 min → 423 Locked.
- [ ] `/auth/me` requires Bearer; returns user DTO.
- [ ] Coverage on `auth_service` ≥ 90%.
- [ ] No PII (email, password, token) in any log line.

### 9.5 Edge Cases (handled in code + tests)

| Case                          | Behavior                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------- |
| Email already exists          | 409 `EMAIL_TAKEN` (only on signup; login stays generic)                         |
| Expired access                | 401; client refreshes                                                           |
| Expired refresh               | 401 `REFRESH_EXPIRED`; force re-login                                           |
| Reused refresh                | 401 `REFRESH_REUSED`; family revoked                                            |
| Account locked                | 423 `ACCOUNT_LOCKED` with `Retry-After`                                         |
| Password change               | Revoke all refresh families                                                     |
| Concurrent refresh (two tabs) | DB unique constraint serializes; loser gets 401, refetches with surviving token |

### 9.6 Risks & Mitigations

| Risk                                                | Mitigation                                                               |
| --------------------------------------------------- | ------------------------------------------------------------------------ |
| Cookie not sent cross-port in dev (5173 ↔ 8000)     | Use Vite proxy: `vite.config.ts` proxies `/v1` → `http://localhost:8000` |
| `SameSite=Strict` blocks the cookie on cross-origin | Frontend served same-site in production via Railway                      |
| JWT secrets leaked in logs                          | `model_config: extra="forbid"` + `SecretStr` for password fields         |

### 9.7 Rollback

```bash
alembic downgrade -2     # drop refresh_tokens + users
git revert <PR-merge-sha>
```

---

## 10. Phase 3 — Project Management Module

**Goal:** Authenticated users can create projects, invite existing users, manage roles, soft-delete; every mutation writes to ActivityLog.

**Branch:** `feat/p3-projects`

**Prereqs:** Phase 2.

### 10.1 Tasks

1. Add `Project`, `ProjectMember`, `ActivityLog` models + migrations.
2. Add `projects_repo`, `project_members_repo`, `activity_repo`.
3. Add `project_service` (create, list, get, update, soft_delete, transfer_owner).
4. Add `member_service` (invite, list, change_role, remove, last_admin_check).
5. Add `activity_service.log()` helper used by all services.
6. Add RBAC deps: `require_project_member`, `require_project_admin` (cf. spec §4.7).
7. Add routes per spec §10.3.
8. Use `404` for non-member reads (no enumeration).
9. Tests: full RBAC matrix (cf. spec §4.2).

### 10.2 Service Pattern (canonical example)

```python
class ProjectService:
    def __init__(self, projects: ProjectsRepo, members: ProjectMembersRepo,
                 activity: ActivityRepo) -> None:
        self.projects = projects
        self.members = members
        self.activity = activity

    async def create(self, db: AsyncSession, *, user: User, payload: ProjectCreate) -> Project:
        if await self.projects.exists_by_name(db, owner_id=user.id, name=payload.name):
            raise BusinessError("PROJECT_NAME_TAKEN", status=409)
        project = await self.projects.create(db, owner_id=user.id, **payload.model_dump())
        await self.members.add(db, project_id=project.id, user_id=user.id,
                                role=ProjectRole.ADMIN, invited_by=user.id)
        await self.activity.log(db, actor_id=user.id, project_id=project.id,
                                entity_type="project", entity_id=project.id,
                                action="PROJECT_CREATED", metadata={"name": project.name})
        return project
```

### 10.3 Commit Sequence

| #   | Type | Message                                                               |
| --- | ---- | --------------------------------------------------------------------- |
| 1   | feat | `feat(db): add Project model and migration`                           |
| 2   | feat | `feat(db): add ProjectMember with unique (project, user)`             |
| 3   | feat | `feat(db): add ActivityLog with jsonb metadata`                       |
| 4   | feat | `feat(repos): add projects, members, activity repositories`           |
| 5   | feat | `feat(auth): add require_project_member + require_project_admin deps` |
| 6   | feat | `feat(projects): service + routes for CRUD`                           |
| 7   | feat | `feat(projects): enforce 404 on non-member reads`                     |
| 8   | feat | `feat(members): invite by email of existing user`                     |
| 9   | feat | `feat(members): change role + remove + last-admin guard`              |
| 10  | feat | `feat(projects): transfer ownership endpoint`                         |
| 11  | feat | `feat(activity): write log entries in same transaction`               |
| 12  | test | `test(projects): RBAC matrix (admin × member × non-member)`           |
| 13  | test | `test(members): last-admin demotion blocked`                          |
| 14  | test | `test(members): cannot remove owner without transfer`                 |

### 10.4 Acceptance Criteria

- [ ] Creator auto-added as Admin.
- [ ] Non-member `GET /projects/{id}` → `404 PROJECT_NOT_FOUND` (not 403).
- [ ] Member CANNOT update project metadata → `403`.
- [ ] Demoting the last Admin → `409 LAST_ADMIN`.
- [ ] Owner cannot be removed without `POST /transfer-owner`.
- [ ] ActivityLog row written for every mutation; rolled back on error.
- [ ] Coverage on services ≥ 85%.

### 10.5 Risks

| Risk                               | Mitigation                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------------ |
| 404 vs 403 mistakes leak existence | Centralize in `require_project_member` — never raise 403 if membership lookup fails. |
| Forgetting to log activity         | Activity write is the **last** step in every service method; reviewers grep for it.  |
| `ON DELETE` cascading by accident  | Migrations explicit; reviewed line-by-line.                                          |

---

## 11. Phase 4 — Task Management Module

**Goal:** Full task CRUD with status FSM, filters, assignment validation, optimistic concurrency, and audit logs.

**Branch:** `feat/p4-tasks`

**Prereqs:** Phase 3.

### 11.1 Tasks

1. Add `Task` model + migration (cf. spec §9.2).
2. Add `TaskStatus`, `TaskPriority` enums.
3. Add `tasks_repo` with paginated list + filters.
4. Add `task_service` with FSM + assignee validation + concurrency check.
5. Add routes: create, list, get, patch, status patch, soft-delete.
6. Add `If-Match` header check; mismatch → `412 PRECONDITION_FAILED`.
7. Cascade: when a member is removed → null their assignments + log.
8. Tests for every FSM transition + every error code.

### 11.2 Filters & Pagination Contract

```
GET /v1/projects/{id}/tasks?
    status=todo,in_progress
   &assignee_id=<uuid>
   &priority=high,critical
   &due_before=2026-06-01
   &q=keyword
   &page=1
   &size=20
   &sort=-priority,created_at
```

Repo applies in this order: scope by project → filter → search → sort → paginate. Hard cap `size ≤ 100`.

### 11.3 Optimistic Concurrency

```python
async def update(db, *, task: Task, payload: TaskUpdate, if_match: datetime | None):
    if if_match is not None and task.updated_at != if_match:
        raise BusinessError("PRECONDITION_FAILED", status=412,
                            details={"current_updated_at": task.updated_at.isoformat()})
    ...
```

### 11.4 Commit Sequence

| #   | Type | Message                                                                            |
| --- | ---- | ---------------------------------------------------------------------------------- |
| 1   | feat | `feat(db): add Task model with enums and migration`                                |
| 2   | feat | `feat(db): add partial indexes for tasks (project_alive, assignee_open, due_date)` |
| 3   | feat | `feat(repos): add tasks repo with filters and pagination`                          |
| 4   | feat | `feat(tasks): service with FSM enforcement`                                        |
| 5   | feat | `feat(tasks): validate assignee is project member`                                 |
| 6   | feat | `feat(tasks): routes for CRUD + /status`                                           |
| 7   | feat | `feat(tasks): If-Match optimistic concurrency`                                     |
| 8   | feat | `feat(members): null assignee on member removal`                                   |
| 9   | feat | `feat(activity): log all task mutations`                                           |
| 10  | test | `test(tasks): FSM allowed and rejected transitions`                                |
| 11  | test | `test(tasks): filters + pagination + sort`                                         |
| 12  | test | `test(tasks): If-Match mismatch returns 412`                                       |
| 13  | test | `test(members): removal nulls assignments`                                         |

### 11.5 Acceptance Criteria

- [ ] `PATCH /tasks/{id}/status` enforces FSM; rejected transitions return 422 with `allowed` list.
- [ ] Assigning to non-member → 422 `ASSIGNEE_NOT_MEMBER`.
- [ ] Completing sets `completed_at`; reopen clears it.
- [ ] Stale `If-Match` → 412.
- [ ] Member removal nullifies their assignments and writes a log entry.
- [ ] `size > 100` clamped to 100; no DoS via large pages.

### 11.6 Risks

| Risk                                      | Mitigation                                                      |
| ----------------------------------------- | --------------------------------------------------------------- |
| N+1 on list endpoint (member lookups)     | `selectinload(Task.assignee)`                                   |
| Date timezone bugs                        | `due_date` is `DATE` (no time); compared to DB `CURRENT_DATE`.  |
| FSM rules drift between client and server | Server is the only authority; client just suggests transitions. |

---

## 12. Phase 5 — Frontend Foundation

**Goal:** Vite + React + TS app with auth flow working end-to-end against the live backend.

**Branch:** `feat/p5-frontend-foundation`

**Prereqs:** Phase 2 (API contracts stable).

### 12.1 Tasks

1. Configure Vite: path alias `@/`, env types, dev proxy `/v1 → :8000`.
2. Configure Tailwind with design tokens (cf. spec §14).
3. Add `QueryClient` with sane defaults (`staleTime: 30_000`, `retry: 3`).
4. Add Zustand `auth` store: `accessToken`, `user`, `setSession`, `clearAuth`.
5. Add Axios client with request interceptor (Bearer) + response interceptor (refresh-on-401-once).
6. Add router with lazy routes and `<ProtectedRoute>`.
7. Add design-system primitives: Button, Input, Card, Toast, Skeleton, Dialog (atop Radix).
8. Add Auth pages: `/signup`, `/login`.
9. Add shell: AppShell with sidebar + topbar.
10. Boot flow: on mount → `GET /auth/me` → hydrate Zustand; gate routes accordingly.

### 12.2 Axios Refresh Race-Safe Interceptor

```ts
// src/lib/api/client.ts (abridged; full pattern in spec §13.4)
let inflightRefresh: Promise<string | null> | null = null;

async function attemptRefresh(): Promise<string | null> {
  inflightRefresh ??= api
    .post("/auth/refresh")
    .then((r) => r.data.data.access_token as string)
    .catch(() => null)
    .finally(() => {
      inflightRefresh = null;
    });
  return inflightRefresh;
}
```

All concurrent 401s share one refresh promise — prevents double-rotation.

### 12.3 Commit Sequence

| #   | Type  | Message                                                               |
| --- | ----- | --------------------------------------------------------------------- |
| 1   | chore | `chore(web): configure Vite path alias and dev proxy`                 |
| 2   | chore | `chore(web): configure tailwind with design tokens`                   |
| 3   | feat  | `feat(web): add QueryClient with defaults`                            |
| 4   | feat  | `feat(web): add Zustand auth store`                                   |
| 5   | feat  | `feat(web): add axios client with bearer + refresh interceptor`       |
| 6   | feat  | `feat(web): add UI primitives (Button, Input, Card, Toast, Skeleton)` |
| 7   | feat  | `feat(web): add Dialog primitive on Radix`                            |
| 8   | feat  | `feat(web): add router with lazy routes`                              |
| 9   | feat  | `feat(web): add ProtectedRoute HOC`                                   |
| 10  | feat  | `feat(web): add LoginPage with RHF + Zod`                             |
| 11  | feat  | `feat(web): add SignupPage with RHF + Zod`                            |
| 12  | feat  | `feat(web): add AppShell with sidebar and topbar`                     |
| 13  | feat  | `feat(web): hydrate auth via /auth/me on boot`                        |
| 14  | test  | `test(web): unit test refresh interceptor race`                       |

### 12.4 Acceptance Criteria

- [ ] Signup → automatic login → land on `/dashboard` (empty state for now).
- [ ] Reload → still logged in (refresh cookie + `/auth/me` boot hydration).
- [ ] Logout → cookies cleared, redirect to `/login`.
- [ ] Expired access token transparently refreshed once; user never sees a 401.
- [ ] `pnpm lint && pnpm typecheck && pnpm test --run` green.
- [ ] Lighthouse a11y ≥ 95 on auth pages.

### 12.5 Risks

| Risk                                         | Mitigation                                                    |
| -------------------------------------------- | ------------------------------------------------------------- |
| Refresh interceptor infinite loop            | `config._retry` flag set on the retried request.              |
| Vite dev cookie SameSite issues              | Use Vite proxy; backend issues cookies on the proxied origin. |
| Hydration race (rendering before `/auth/me`) | `<FullPageSkeleton>` while `isLoading` is true.               |

---

## 13. Phase 6 — Dashboard & Analytics

**Goal:** Per-user dashboard with stat cards, my-tasks, recent-activity feed.

**Branch:** `feat/p6-dashboard`

**Prereqs:** Phases 4 + 5.

### 13.1 Tasks

1. Add `dashboard_service` with aggregation SQL (one query per widget).
2. Add `/v1/dashboard/stats`, `/v1/dashboard/my-tasks`, `/v1/dashboard/recent-activity` routes.
3. (Optional) Redis cache: TTL 60 s on stats; gracefully degrade if Redis unavailable.
4. Build dashboard page: StatCard grid, MyTasks list, RecentActivity feed.
5. Charts: counts-by-status (simple) — defer rich charts to later.

### 13.2 Aggregation Example

```python
async def stats(db, user_id) -> DashboardStats:
    sql = text("""
      SELECT
        COUNT(*) FILTER (WHERE t.status <> 'done')                                  AS open,
        COUNT(*) FILTER (WHERE t.status <> 'done' AND t.due_date < CURRENT_DATE)    AS overdue,
        COUNT(*) FILTER (WHERE t.status <> 'done' AND t.due_date <= CURRENT_DATE + 7) AS due_week
      FROM tasks t
      JOIN project_members m ON m.project_id = t.project_id
      WHERE m.user_id = :uid AND t.deleted_at IS NULL
    """)
    row = (await db.execute(sql, {"uid": user_id})).one()
    return DashboardStats(open=row.open, overdue=row.overdue, due_this_week=row.due_week)
```

### 13.3 Commit Sequence

| #   | Type | Message                                                |
| --- | ---- | ------------------------------------------------------ |
| 1   | feat | `feat(dashboard): service with aggregate SQL queries`  |
| 2   | feat | `feat(dashboard): /v1/dashboard/stats route`           |
| 3   | feat | `feat(dashboard): /v1/dashboard/my-tasks route`        |
| 4   | feat | `feat(dashboard): /v1/dashboard/recent-activity route` |
| 5   | feat | `feat(dashboard): optional redis cache with TTL`       |
| 6   | feat | `feat(web): DashboardPage with stat cards`             |
| 7   | feat | `feat(web): MyTasks list component`                    |
| 8   | feat | `feat(web): RecentActivity feed component`             |
| 9   | test | `test(dashboard): aggregations match underlying data`  |
| 10  | test | `test(dashboard): respects RBAC scope`                 |

### 13.4 Acceptance Criteria

- [ ] Counts match: a user creating 3 tasks (2 open, 1 done) sees exactly that.
- [ ] Overdue logic: `due_date < today AND status <> done`.
- [ ] Without Redis: works (only slower). With Redis: same correctness.
- [ ] Empty user (no projects) sees CTA, not error.

### 13.5 Performance Targets

- p95 < 100 ms for each dashboard endpoint at 10k tasks per user.
- One query per endpoint (verify with logging in dev).

---

## 14. Phase 7 — UI Polish & UX

**Goal:** Production-quality UI: empty/error/loading states, toasts, a11y, mobile.

**Branch:** `feat/p7-ui-polish`

**Prereqs:** Phase 6.

### 14.1 Tasks

1. Replace bare spinners with skeleton screens matching final layout.
2. Empty states for: Projects, Tasks, Dashboard, Members, Activity.
3. Error boundaries at: page, query, mutation level. Show request-id.
4. Toast system: success (4 s, auto), error (sticky with retry).
5. Keyboard shortcuts: `c` create, `/` focus search, `g d` go dashboard, `Esc` close dialog.
6. Mobile pass: 360 px viewport; sidebar → drawer; tables → cards.
7. Accessibility audit: axe-core in CI; fix every critical.
8. Dark mode toggle (Tailwind `dark:`).

### 14.2 Commit Sequence

| #   | Type     | Message                                                    |
| --- | -------- | ---------------------------------------------------------- |
| 1   | feat     | `feat(ui): add skeleton screens for project + task lists`  |
| 2   | feat     | `feat(ui): add empty state component and copy`             |
| 3   | feat     | `feat(ui): add toast provider with success/error variants` |
| 4   | feat     | `feat(ui): add error boundary surfacing request-id`        |
| 5   | feat     | `feat(ui): add keyboard shortcut layer`                    |
| 6   | refactor | `refactor(ui): collapse sidebar into drawer below md`      |
| 7   | refactor | `refactor(ui): turn tables into card lists below md`       |
| 8   | feat     | `feat(ui): add dark mode toggle`                           |
| 9   | chore    | `chore(ci): add axe-core check on key pages`               |

### 14.3 Acceptance Criteria

- [ ] No bare spinners > 300 ms anywhere.
- [ ] Every list has an empty state with an actionable CTA.
- [ ] Every mutation has a toast on success and error.
- [ ] Lighthouse a11y ≥ 95 on every page.
- [ ] 360 px viewport renders without horizontal scroll.
- [ ] Tab order is sensible on every form.

---

## 15. Phase 8 — Testing & QA

**Goal:** Coverage gates, Playwright golden paths, CI nightly E2E.

**Branch:** `feat/p8-testing-qa`

**Prereqs:** Phase 7.

### 15.1 Test Strategy (recap from spec §19)

| Layer               | Tool                     | Target                       |
| ------------------- | ------------------------ | ---------------------------- |
| Unit (BE)           | pytest                   | ≥ 90% on services            |
| Integration (BE)    | pytest + httpx + real PG | every endpoint at least once |
| Unit/component (FE) | Vitest + RTL             | ≥ 70% statements             |
| E2E                 | Playwright               | golden paths only            |

### 15.2 Backend Test Fixtures (canonical)

```python
# tests/conftest.py
@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with engine.begin() as conn:
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
            await session.rollback()  # auto-rollback per-test

@pytest_asyncio.fixture
async def client(db_session) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_headers(client) -> dict:
    r = await client.post("/v1/auth/signup",
        json={"email": "u@e.com", "name": "U", "password": "VeryStrong123!"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}
```

### 15.3 Playwright Golden Path

```ts
// apps/web/e2e/golden.spec.ts
test("signup → project → invite → task → done", async ({ page }) => {
  await page.goto("/signup");
  await page.getByLabel("Email").fill(`u+${Date.now()}@test.io`);
  // ...
});
```

### 15.4 Commit Sequence

| #   | Type | Message                                               |
| --- | ---- | ----------------------------------------------------- |
| 1   | test | `test(api): add base fixtures with per-test rollback` |
| 2   | test | `test(api): add factory-boy factories`                |
| 3   | test | `test(projects): cover full RBAC matrix`              |
| 4   | test | `test(tasks): cover FSM exhaustively`                 |
| 5   | test | `test(web): unit tests for axios refresh logic`       |
| 6   | test | `test(web): component tests for forms`                |
| 7   | test | `test(e2e): playwright golden path`                   |
| 8   | ci   | `ci(workflows): enforce 80% backend coverage gate`    |
| 9   | ci   | `ci(workflows): add nightly e2e workflow`             |

### 15.5 Acceptance Criteria

- [ ] `pytest --cov-fail-under=80` passes in CI.
- [ ] `pnpm test --coverage` ≥ 70% statements.
- [ ] Playwright E2E green on `main`.
- [ ] CI artifacts include Playwright trace on failure.

---

## 16. Phase 9 — Deployment & Production

**Goal:** Live URL on Railway with managed PostgreSQL, env vars, migrations-on-deploy, health checks, monitoring.

**Branch:** `chore/p9-deploy`

**Prereqs:** Phase 8.

### 16.1 Railway Services

| Service            | Purpose         | Build                                          | Start                                                                                  |
| ------------------ | --------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| `api`              | FastAPI backend | `uv sync --no-dev`                             | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2` |
| `web`              | React SPA       | `pnpm install --frozen-lockfile && pnpm build` | `node serve.js` (or static adapter)                                                    |
| `postgres`         | Managed addon   | —                                              | —                                                                                      |
| `redis` (optional) | Managed addon   | —                                              | —                                                                                      |

### 16.2 `apps/api/railway.toml`

```toml
[build]
builder = "NIXPACKS"
buildCommand = "uv sync --frozen --no-dev"

[deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/v1/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
numReplicas = 1
```

### 16.3 `apps/web/railway.toml`

```toml
[build]
builder = "NIXPACKS"
buildCommand = "corepack enable && pnpm install --frozen-lockfile && pnpm build"

[deploy]
startCommand = "pnpm dlx serve -s dist -l $PORT"
healthcheckPath = "/"
healthcheckTimeout = 10
restartPolicyType = "ON_FAILURE"
```

### 16.4 Steps

1. `railway init` → create project; link services.
2. `railway add` → PostgreSQL plugin.
3. Set env vars per spec §22 (`railway variables set KEY=VALUE --service api`).
4. Configure custom domains, TLS auto-issued.
5. First deploy: trigger from CLI (`railway up --service api`) or push to `main`.
6. Verify `/v1/health` returns 200.
7. Smoke test: signup → create project → create task → mark done.
8. Configure Sentry DSN; verify a manual error reaches Sentry.
9. Set up Railway metrics alerts (5xx rate > 1% for 5 min → notify).

### 16.5 Commit Sequence

| #   | Type  | Message                                                     |
| --- | ----- | ----------------------------------------------------------- |
| 1   | chore | `chore(deploy): add railway.toml for api service`           |
| 2   | chore | `chore(deploy): add railway.toml for web service`           |
| 3   | chore | `chore(deploy): document env vars in .env.example`          |
| 4   | feat  | `feat(api): /v1/health pings DB and returns version`        |
| 5   | chore | `chore(deploy): add seed script for first-deploy demo user` |
| 6   | docs  | `docs(runbooks): add deploy.md + rollback.md`               |
| 7   | docs  | `docs(readme): add demo credentials and live URL`           |

### 16.6 Rollback Strategy

| Failure                      | Action                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------ |
| Migration fails              | Deploy halts; previous service stays live. Investigate locally with prod DB clone.   |
| Code regression after deploy | Railway → previous deployment → "Redeploy".                                          |
| Bad migration on live data   | `alembic downgrade -1` from `railway run` if reversible; else point-in-time restore. |
| Cookies/CORS broken in prod  | Check `FRONTEND_URLS`, custom domain, SameSite. Patch + redeploy.                    |

### 16.7 Acceptance Criteria

- [ ] `https://<your-domain>` loads.
- [ ] Signup + login work end-to-end on production URL.
- [ ] `/v1/health` returns 200 within 5 s.
- [ ] Sentry receives a test error.
- [ ] Database backups verified (Railway daily snapshot).
- [ ] Rollback rehearsed once.
- [ ] All checks in §30 pass.

---

## 17. CI/CD Pipeline

### 17.1 `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    name: Backend (py 3.12)
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ttm_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 3s --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/ttm_test
      JWT_SECRET: ci-jwt-secret-not-for-production-min-32-bytes
      JWT_REFRESH_SECRET: ci-jwt-refresh-secret-not-for-production-min-32-bytes
      FRONTEND_URLS: '["http://localhost:5173"]'
      ENVIRONMENT: test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
          cache-dependency-glob: "apps/api/uv.lock"
      - name: Install deps
        working-directory: apps/api
        run: uv sync --frozen
      - name: Ruff
        working-directory: apps/api
        run: uv run ruff check .
      - name: Black
        working-directory: apps/api
        run: uv run black --check .
      - name: Mypy
        working-directory: apps/api
        run: uv run mypy .
      - name: Migrate
        working-directory: apps/api
        run: uv run alembic upgrade head
      - name: Test
        working-directory: apps/api
        run: uv run pytest --cov=app --cov-report=xml --cov-fail-under=80
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: backend-coverage, path: apps/api/coverage.xml }

  frontend:
    name: Frontend (node 20)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm -F web lint
      - run: pnpm -F web typecheck
      - run: pnpm -F web test --run --coverage
      - run: pnpm -F web build
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: web-dist, path: apps/web/dist }

  commitlint:
    name: Commitlint
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: pnpm/action-setup@v3
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm exec commitlint --from ${{ github.event.pull_request.base.sha }} --to HEAD
```

### 17.2 `.github/workflows/e2e.yml`

```yaml
name: E2E

on:
  schedule: [{ cron: "0 6 * * *" }] # nightly
  workflow_dispatch:

jobs:
  playwright:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_PASSWORD: postgres, POSTGRES_DB: ttm_e2e }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: pnpm/action-setup@v3
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - working-directory: apps/api
        env: { DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/ttm_e2e }
        run: |
          uv sync --frozen
          uv run alembic upgrade head
          uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 2
      - run: pnpm install --frozen-lockfile
      - run: pnpm -F web exec playwright install --with-deps chromium
      - run: pnpm -F web build && pnpm -F web exec playwright test
        env: { VITE_API_BASE_URL: http://localhost:8000/v1 }
      - uses: actions/upload-artifact@v4
        if: failure()
        with: { name: playwright-report, path: apps/web/playwright-report }
```

### 17.3 `.github/workflows/deploy-trigger.yml`

```yaml
# Optional: explicit deploy after CI passes on main.
# Railway's GitHub integration auto-deploys main on push — this workflow is for safety nets and notifications.
name: Deploy notify
on:
  push:
    branches: [main]
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Railway is deploying $GITHUB_SHA — watch logs."
```

### 17.4 Cache Strategy

| Cache               | Where                              | Hit benefit          |
| ------------------- | ---------------------------------- | -------------------- |
| `uv` cache          | `astral-sh/setup-uv@v3`            | ~30 s → ~3 s install |
| pnpm store          | `actions/setup-node@v4 cache:pnpm` | ~40 s → ~5 s install |
| Playwright browsers | `~/.cache/ms-playwright`           | ~60 s → ~5 s         |

### 17.5 Failure Notifications

- GitHub native PR check status.
- Railway webhook → Slack (optional, configure in Railway dashboard).
- Sentry alerts for prod errors.

---

## 18. Database Architecture & Migration Strategy

### 18.1 Alembic Conventions

```python
# app/db/base.py
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

Why: autogenerate produces stable, deterministic constraint names; drift between developers eliminated.

### 18.2 Schema Evolution Rules

1. **Expand → migrate code → contract** for any schema change touching live data.
2. Every migration **must** be reversible (`downgrade()` implemented) unless documented exception.
3. **No DDL during high-traffic windows**; Railway has near-zero traffic at deploy.
4. Add columns nullable first; backfill in next deploy; tighten to NOT NULL in the deploy after.
5. **Rename a column?** Three-step: add new, dual-write, drop old. Never rename in one migration on production data.

### 18.3 Production-Safe Migration Patterns

| Change                           | Steps                                                 |
| -------------------------------- | ----------------------------------------------------- |
| Add nullable column              | 1 migration                                           |
| Add NOT NULL column with default | 1 migration (server_default)                          |
| Rename column                    | 3 migrations across 3 deploys                         |
| Drop column                      | 2 migrations: stop reading → drop                     |
| Change column type               | Expand (add new) → migrate code → contract (drop old) |
| Add index                        | `CREATE INDEX CONCURRENTLY` via raw `op.execute`      |

### 18.4 Reset Strategy

```bash
make reset-db          # drop + recreate + migrate (local only)
```

Never reset prod. For full re-seed in staging: `railway run alembic downgrade base && railway run alembic upgrade head`.

### 18.5 Seeding

`scripts/seed.py` creates a demo user + project + tasks. Idempotent: checks existence before insert.

### 18.6 Backup Strategy

- Railway managed PG: daily snapshot + point-in-time recovery (within retention window).
- Monthly **restore drill**: clone snapshot to a staging project, run migrations, sanity test.
- Backups must include `activity_logs` (forensics asset).

### 18.7 Indexing Strategy

Already documented in spec §9.3. Audit cadence: every quarter run `EXPLAIN ANALYZE` on the top-10 endpoints; track index hit rate via `pg_stat_user_indexes`.

---

## 19. API Architecture Standards

### 19.1 Layer Contract

```
Router ──► Service ──► Repository ──► ORM
   ▲          ▲           ▲
   │          │           └─ no business rules
   │          └─ no SQL outside parameterized queries via ORM/repo
   └─ no DB session direct use; only Depends
```

### 19.2 Pydantic Conventions

| Concern      | Pattern                                                      |
| ------------ | ------------------------------------------------------------ |
| Request body | `*Create`, `*Update` schemas with `extra="forbid"`           |
| Response     | Explicit `response_model=*Read` per endpoint                 |
| Internal DTO | Optional, only when ORM model differs from response          |
| Errors       | `BusinessError(code: ErrorCode, status: int, details: dict)` |

### 19.3 Pagination / Filter / Sort Grammar

```
?page=1&size=20             # offset paging; size capped 100
?sort=-priority,created_at  # comma-separated, `-` for desc
?status=todo,in_progress    # csv enum filter
?q=keyword                  # case-insensitive search
?due_before=2026-06-01      # ISO date
```

Standard `PaginationParams` dep:

```python
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
```

### 19.4 Standard Envelopes

(See spec §10.2.) Implemented via `Envelope[T]` generic Pydantic model + `ResponseBuilder` helper.

### 19.5 OpenAPI

- Auto-generated from Pydantic; surfaced at `/docs` in non-prod.
- Exported via `make openapi` → `apps/api/openapi.json` (committed for downstream clients).
- Pre-commit: regenerate when schemas change.

### 19.6 API Versioning

- Prefix `/v1` from day 1.
- Breaking change = new version (`/v2`); old maintained for ≥ 90 days.
- Non-breaking additions go into `/v1`.

---

## 20. Frontend Architecture Standards

### 20.1 Component Split

| Type               | Examples                | Rules                                                   |
| ------------------ | ----------------------- | ------------------------------------------------------- |
| **Pages**          | `ProjectsListPage`      | Compose containers + layout; no data fetching directly. |
| **Containers**     | `ProjectsListContainer` | Use hooks (`useProjects`), pass props down.             |
| **Presentational** | `ProjectCard`           | Pure; props in, JSX out; storybook-able.                |
| **Primitives**     | `Button`, `Input`       | Headless+styled; in `components/ui/`.                   |

### 20.2 Hook Patterns

```ts
// src/features/projects/hooks.ts
export function useProjects(params: ListParams) {
  return useQuery({
    queryKey: ["projects", "list", params] as const,
    queryFn: () => projectsApi.list(params),
    staleTime: 30_000,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}
```

### 20.3 Query Key Conventions

```
["projects"]                                  # all projects
["projects", "list", params]                  # list with filters
["projects", projectId]                       # one project
["projects", projectId, "members"]            # members
["projects", projectId, "tasks", params]      # tasks list
["tasks", taskId]                             # single task
["auth", "me"]                                # current user
["dashboard", "stats"]                        # stats
```

Invalidate by prefix: `qc.invalidateQueries({ queryKey: ["projects", projectId] })` clears the project and its members/tasks.

### 20.4 Form Pattern

```tsx
const form = useForm<TaskCreate>({
  resolver: zodResolver(TaskCreateSchema),
  defaultValues: { title: "", priority: "medium" },
});

const create = useCreateTask();

const onSubmit = form.handleSubmit(async (values) => {
  try {
    await create.mutateAsync(values);
    toast.success("Task created");
  } catch (e) {
    applyApiErrorsToForm(form, e); // maps field-level details from envelope
  }
});
```

### 20.5 Error Handling

- API errors normalized in axios interceptor → throw `ApiError(code, message, details, request_id)`.
- Mutations toast on error; queries surface via `ErrorState` component.
- ErrorBoundary at root catches render exceptions → friendly page + request-id.

### 20.6 State Normalization

- Server data lives in TanStack Query cache; no duplication into Zustand.
- Client UI state (modals, sidebar) in Zustand.
- URL state (filters, pagination) in `useSearchParams` for shareable links.

---

## 21. Security Architecture

(See also spec §17 for the OWASP matrix and threat-model summary. This section adds **execution discipline**.)

### 21.1 Boot-Time Validation

- `Settings()` raises if any required env var is missing or malformed.
- Production env check: refuse to start if `ENVIRONMENT=production` and `DOCS_ENABLED=true`.

### 21.2 Secret Rotation Runbook (`docs/runbooks/secret-rotation.md`)

| Secret                  | Rotation cadence           | Procedure                                                                           |
| ----------------------- | -------------------------- | ----------------------------------------------------------------------------------- |
| `JWT_SECRET`            | Quarterly or on compromise | Set new on Railway → restart → existing sessions invalidated (acceptable trade-off) |
| `JWT_REFRESH_SECRET`    | Same as above              | Same; invalidates refresh tokens                                                    |
| `DATABASE_URL` password | On Railway rotate          | Triggers redeploy automatically                                                     |
| Sentry DSN              | Per project                | Update env var; restart                                                             |

### 21.3 Rate Limiting

- `slowapi` with Redis backend in production; in-memory in dev.
- Limits per spec §17.6.
- Lockout: 10 failed logins / 5 min / email → 15-min cool-down.

### 21.4 CORS

```python
FRONTEND_URLS=["https://app.example.com"]  # exact match list
# never "*", never patterns
```

### 21.5 Dependency Audit

- CI weekly: `pip-audit` + `pnpm audit --prod`.
- Critical findings: open issue + patch within 7 days.

### 21.6 Headers

```python
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### 21.7 Threat Mitigation Summary

| Threat            | Mitigation                                                          |
| ----------------- | ------------------------------------------------------------------- |
| Brute-force login | Rate limit + lockout + constant-time bcrypt                         |
| Token theft       | Short access TTL + rotation + reuse detection                       |
| CSRF              | SameSite=Strict on refresh cookie + Bearer header for state changes |
| XSS               | React auto-escape + ESLint ban on `dangerouslySetInnerHTML`         |
| SQL injection     | ORM parameterized queries only                                      |
| Open redirect     | No URL redirects from user input                                    |
| Mass assignment   | Pydantic `extra="forbid"` on all `*Update` schemas                  |

---

## 22. Error Handling & Logging Strategy

### 22.1 Error Classes

```python
class BusinessError(Exception):
    def __init__(self, code: ErrorCode, *, status: int = 400,
                 message: str | None = None, details: dict | None = None) -> None:
        self.code = code
        self.status = status
        self.message = message or code.default_message
        self.details = details or {}
```

### 22.2 Exception Handler Wiring

```python
def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def be(_, exc: BusinessError):
        return ORJSONResponse(status_code=exc.status, content=error_envelope(exc))

    @app.exception_handler(RequestValidationError)
    async def ve(_, exc):
        return ORJSONResponse(status_code=422, content=validation_envelope(exc))

    @app.exception_handler(IntegrityError)
    async def ie(_, exc):
        code = constraint_to_code(exc)
        return ORJSONResponse(status_code=409, content=error_envelope(BusinessError(code)))

    @app.exception_handler(Exception)
    async def fb(request, exc):
        logger.exception("unhandled", exc_info=exc)
        return ORJSONResponse(status_code=500, content=error_envelope_internal())
```

### 22.3 Structured Logging

```python
# app/core/logging.py
import structlog

def configure_logging() -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.ENVIRONMENT in ("local", "test"):
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    structlog.configure(processors=processors)
```

### 22.4 Request Correlation

```python
class RequestIDMiddleware:
    async def __call__(self, scope, receive, send):
        request_id = headers.get("X-Request-Id") or new_id()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        # ...send response with X-Request-Id header...
```

### 22.5 Log Levels

| Level      | Use                         | Examples                                   |
| ---------- | --------------------------- | ------------------------------------------ |
| `DEBUG`    | Local only                  | SQL echo, hot-loop noise                   |
| `INFO`     | Request lifecycle           | "request_started", "request_completed"     |
| `WARNING`  | Degraded                    | "cache_miss", "redis_unavailable_fallback" |
| `ERROR`    | Handled failure with action | "external_api_failed", "business_error"    |
| `CRITICAL` | Unhandled / system-wide     | Caught only by fallback handler            |

4xx never logged at ERROR; 5xx always.

### 22.6 PII Hygiene

- Never log `password`, `token`, full `email` (mask to `u***@example.com` if needed).
- CI test asserts `pytest tests/test_logging_pii.py` — uses captured logs.

### 22.7 Debugging Workflow

1. Reproduce locally if possible.
2. Grep production logs by `request_id`.
3. Use Sentry's grouping to find pattern.
4. If DB-related: `EXPLAIN ANALYZE` on the offending query.
5. Add regression test before fixing.

---

## 23. Performance Optimization Plan

### 23.1 Query Budgets

| Endpoint class      | Max queries                        | Reason                    |
| ------------------- | ---------------------------------- | ------------------------- |
| GET single resource | 2 (RBAC + fetch)                   | Includes membership check |
| GET list            | 3 (RBAC + count + page)            | + 1 if joined-load        |
| POST/PATCH          | 4 (RBAC + load + write + activity) | Activity log included     |
| DELETE              | 3                                  |                           |

CI hint: assert query counts in critical integration tests via SQLAlchemy event hooks.

### 23.2 Eager Loading

- `selectinload(Task.assignee)` on task lists.
- `selectinload(Project.members).selectinload(ProjectMember.user)` on project detail.

### 23.3 Pagination

- Cap `size ≤ 100` server-side.
- Future cursor migration: ADR-0002 covers semantics; switch when offset pagination hits its breaking point (~ 100k rows in a list).

### 23.4 Frontend Bundle Budget

| Asset                | Budget   |
| -------------------- | -------- |
| Initial JS (gzipped) | ≤ 200 KB |
| Total JS (gzipped)   | ≤ 600 KB |
| LCP image            | ≤ 80 KB  |

Tool: `pnpm dlx vite-bundle-visualizer apps/web/dist`.

### 23.5 React Optimization

- `React.memo` on heavy list rows (`TaskCard`, `ProjectCard`).
- `useMemo` for filter computations ≥ O(n).
- `useCallback` only when handler identity matters (passed to memo'd children).
- Avoid prop-drilling beyond 3 levels — extract context or co-locate.

### 23.6 Debounce / Throttle

- Search inputs: debounce 250 ms.
- Window resize handlers: throttle 100 ms.

### 23.7 SQLAlchemy Optimization

- `pool_pre_ping=True` prevents stale-connection errors after Railway upstream blips.
- `expire_on_commit=False` — we control freshness explicitly.
- Bulk inserts use `add_all` for ≤ 100 rows; `bulk_insert_mappings` for ≥ 1000.

### 23.8 Profiling Tools

| Tool                     | Use                                   |
| ------------------------ | ------------------------------------- |
| `py-spy`                 | Sampling profiler in prod (read-only) |
| `EXPLAIN ANALYZE`        | DB query plans                        |
| `pg_stat_statements`     | Top expensive queries in prod         |
| `vite-bundle-visualizer` | Frontend bundle composition           |
| Chrome Performance tab   | Frontend render profiling             |

---

## 24. Edge Cases & Failure Planning

(See also spec §26 for product-level edge cases. This section is **operational**.)

| #   | Failure mode                           | Detection                        | Recovery                                        | User-facing                              |
| --- | -------------------------------------- | -------------------------------- | ----------------------------------------------- | ---------------------------------------- |
| 1   | Failed migration on deploy             | Migration job exits non-zero     | Railway halts; old version stays                | No impact                                |
| 2   | Railway downtime                       | Status page / health check fails | Status banner; cached UI if possible            | Toast "Service unavailable, retry"       |
| 3   | Leaked refresh token                   | Reuse-detection trips            | Family revoked; user re-logs in                 | Sees "Session expired" → login           |
| 4   | CI flake                               | Recurring test failure           | `git rerun` once; if persists, quarantine + fix | None                                     |
| 5   | Lockfile drift                         | CI install fails                 | Run `uv lock` / `pnpm install` locally; commit  | None                                     |
| 6   | DB connection lost                     | `pool_pre_ping` raises           | Endpoint returns 5xx; retry-on-GET in client    | Toast + auto-retry                       |
| 7   | Stale `If-Match`                       | Service returns 412              | UI prompts merge or reload                      | Modal "Task changed elsewhere — reload?" |
| 8   | Concurrent member removal + task edit  | `ASSIGNEE_NOT_MEMBER` raised     | Service nulls assignee in same tx               | UI shows "Unassigned"                    |
| 9   | Token clock skew                       | JWT `iat` future-dated           | 30 s leeway in decoder                          | None                                     |
| 10  | Rate-limit false positive (shared NAT) | 429 for legit user               | Use per-user limits when authenticated          | Soft toast + `Retry-After`               |
| 11  | OpenAPI drift vs client                | Type errors at build             | Regenerate types via `make openapi-types`       | None                                     |
| 12  | Soft-deleted user invited              | `404 USER_NOT_FOUND`             | Admin re-invites once user un-soft-deleted      | "User not found"                         |
| 13  | Sentry not reachable                   | Sentry client buffers + drops    | Logs still emitted to stdout                    | None                                     |
| 14  | Redis down (when wired)                | Cache get fails                  | Code path falls back to DB                      | Slightly slower; no error                |
| 15  | Disk full on PG                        | Write fails                      | Railway alert; scale PG plan                    | 5xx until resolved                       |
| 16  | Stuck deploy                           | `/health` 3 fails                | Railway auto-rollback                           | Brief gap; users retry                   |
| 17  | Long-lived browser tab → token expired | 401 → refresh interceptor        | Single refresh; resume                          | Invisible to user                        |
| 18  | User toggles dark mode mid-mutation    | Re-render                        | Idempotent UI                                   | None                                     |
| 19  | Browser back after logout              | `/auth/me` check on mount        | Redirect to `/login`                            | None                                     |
| 20  | Forced password change on compromise   | All refresh families revoked     | Admin endpoint (future)                         | Users re-login                           |

---

## 25. Local Development Workflow

### 25.1 Daily Startup

```bash
# Once per day
make up                          # postgres in background
make api                         # terminal 1
make web                         # terminal 2

# OR with tmux
tmux new -s ttm \; \
  send-keys 'make up' C-m \; split-window -h \; \
  send-keys 'make api' C-m \; split-window -v \; \
  send-keys 'make web' C-m
```

### 25.2 Feature Loop

```bash
git checkout main && git pull
git checkout -b feat/p4-task-fsm
# ... edit ...
make lint && make test          # green locally before pushing
git add -p                      # stage atomically
git commit -m "feat(tasks): enforce FSM transitions"
git push -u origin HEAD
gh pr create --fill             # uses PR template
```

### 25.3 Migration Loop

```bash
# After editing models
make migration name="add task priority enum"
# review apps/api/alembic/versions/*.py for accuracy
make migrate
make test
```

### 25.4 Debugging Loop

| Symptom      | First step                                                        |
| ------------ | ----------------------------------------------------------------- |
| Backend 500  | Check terminal logs; grep request_id                              |
| 401 loops    | Check axios interceptor logic; inspect Network tab                |
| CORS error   | Check `FRONTEND_URLS` env; check OPTIONS preflight in Network tab |
| Test failure | Run single test with `-x -s`; print fixtures                      |
| Slow query   | `EXPLAIN ANALYZE` in psql                                         |

### 25.5 IDE Setup — VS Code

`.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "eamodio.gitlens",
    "github.vscode-github-actions"
  ]
}
```

`.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/apps/api/.venv/bin/python",
  "python.analysis.typeCheckingMode": "strict",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit",
      "source.fixAll": "explicit"
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "eslint.workingDirectories": ["apps/web"]
}
```

`.vscode/launch.json` (FastAPI debug):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "API: uvicorn (debug)",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/apps/api",
      "env": { "PYTHONUNBUFFERED": "1" }
    },
    {
      "name": "API: pytest current file",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["-x", "-s", "${file}"],
      "cwd": "${workspaceFolder}/apps/api"
    }
  ]
}
```

### 25.6 Productivity Tips

- Alias `gco='git checkout'`, `gcm='git commit -m'`, `gp='git push'`.
- Use `gh pr create --web` to open the PR in the browser.
- `psql $DATABASE_URL` for ad-hoc queries; alias `db` to that.
- `httpie` for hitting `/v1/...` directly: `http POST :8000/v1/auth/login email=u@e.com password=...`.

---

## 26. Commands Reference

### 26.1 pnpm

```bash
pnpm install                              # install all workspaces
pnpm -F web dev                           # run web only
pnpm -F web add zod                       # add dep to web
pnpm -F web add -D vitest                 # add devDep
pnpm dlx <tool>                           # ephemeral run
pnpm -r build                             # build all packages
pnpm format                               # prettier write
```

### 26.2 uv

```bash
uv venv                                   # create .venv
uv sync                                   # install from lockfile
uv sync --frozen                          # CI: error on lockfile drift
uv add fastapi                            # add runtime dep
uv add --dev pytest                       # add dev dep
uv lock --upgrade-package fastapi         # bump one dep
uv run pytest                             # run in project venv without activation
uv python install 3.12                    # install python
```

### 26.3 Alembic

```bash
alembic revision --autogenerate -m "msg"  # new migration
alembic upgrade head                      # apply all
alembic upgrade +1                        # one forward
alembic downgrade -1                      # one back
alembic current                           # show DB version
alembic history -v                        # list revisions
alembic check                             # detect missing autogen diff
```

### 26.4 Railway

```bash
railway login
railway link
railway up                                # deploy current dir
railway up --service api
railway logs --service api --tail
railway run alembic upgrade head          # run command against linked env
railway variables                         # list
railway variables set KEY=VALUE --service api
railway open                              # open dashboard
railway redeploy --service api --deployment <id>   # rollback
```

### 26.5 Git

```bash
git switch -c feat/p3-projects
git add -p                                # stage hunks
git commit -m "feat(projects): ..."
git push -u origin HEAD
git rebase main                           # bring branch up to date
gh pr create --fill
gh pr checks
gh pr merge --squash --delete-branch
```

### 26.6 Docker

```bash
docker compose up -d postgres
docker compose logs postgres -f
docker compose exec -T postgres psql -U postgres
docker compose down                       # stop
docker compose down -v                    # nuke volumes (data loss)
```

### 26.7 Quality

```bash
# Backend
ruff check .
ruff check . --fix
black .
black --check .
mypy .
pytest -q
pytest -x -s -k "test_signup"
pytest --cov=app --cov-report=term-missing

# Frontend
pnpm -F web lint
pnpm -F web typecheck
pnpm -F web test --run
pnpm -F web test --coverage
pnpm -F web exec playwright test
```

### 26.8 Make

```bash
make help            # menu
make bootstrap       # zero-to-running
make up | down       # postgres
make api | web | dev # servers
make migrate
make migration name="..."
make seed
make test | lint | fmt
make reset-db
make openapi
```

---

## 27. Engineering Rules & Code Standards

### 27.1 Frontend (TypeScript)

- **TS strict mode** mandatory; `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
- **No `any`** — `unknown` + narrow. ESLint enforces.
- **No default exports for components** — named only.
- **No barrel files at feature root**.
- **No `console.log`** at merge time (ESLint warn, CI error in prod build).
- **No `dangerouslySetInnerHTML`** — ESLint custom rule.
- **No fetching inside presentational components** — hooks only.
- **No inline styles** except dynamic transforms; Tailwind classes for the rest.
- **One component per file**; file name = component name (PascalCase).
- **Imports order**: external → `@/` → relative.

### 27.2 Backend (Python)

- **Type hints mandatory** on every function (`def f(...) -> ...:`).
- **mypy --strict** in CI; `# type: ignore` requires a comment.
- **No raw SQL** outside repositories.
- **No business logic** in routes or repositories.
- **No module-level mutable state** in services.
- **No `print`**; structlog only.
- **No `from X import *`**.
- **Pydantic `extra="forbid"`** on every `*Update` schema.
- **Every endpoint** has `response_model=`.
- **Every service method** writes to ActivityLog where applicable.

### 27.3 API Conventions

- Plural nouns: `/projects`, `/tasks`.
- Nested for ownership: `/projects/{id}/tasks`.
- Verbs only for non-CRUD: `/projects/{id}/transfer-owner`.
- Status changes via subresource: `PATCH /tasks/{id}/status`.
- Idempotent PUT not used in MVP; PATCH for partial updates.

### 27.4 Component Conventions

| Element         | Rule                                              |
| --------------- | ------------------------------------------------- |
| File            | `TaskCard.tsx` (PascalCase)                       |
| Hook            | `useProjectTasks.ts`                              |
| Test            | `TaskCard.test.tsx` colocated                     |
| Stories         | `TaskCard.stories.tsx` (if Storybook added later) |
| Type-only file  | `types.ts`                                        |
| Index re-export | Allowed at feature root only for **public** API   |

### 27.5 Folder Conventions

- Backend: package per concern (`models/`, `schemas/`, `services/`, `repositories/`).
- Frontend: package per feature (`features/auth/`, `features/projects/`).
- Cross-feature primitives live in `components/ui/`, `lib/`, `hooks/`.
- Tests next to source (frontend); separate `tests/` mirroring `app/` (backend).

---

## 28. Acceptance Criteria Per Phase (Sign-off Master Table)

| Phase | AC summary (full inline in §7–§16)                                                                                | Sign-off |
| ----- | ----------------------------------------------------------------------------------------------------------------- | :------: |
| 0     | `make bootstrap` succeeds; CI green on empty PR; husky rejects bad commits                                        |    ☐     |
| 1     | `/v1/health` ok; alembic head; structlog with request_id; lint+type clean                                         |    ☐     |
| 2     | Signup/login/refresh/logout/me works; refresh rotation + reuse-detection verified; rate limit + lockout active    |    ☐     |
| 3     | Project + member CRUD; 404 vs 403 correct; last-admin/owner rules; activity log per mutation                      |    ☐     |
| 4     | Task CRUD + FSM + assignment validation + If-Match concurrency + member-removal nullifies assignments             |    ☐     |
| 5     | E2E auth on real backend; refresh interceptor race-safe; a11y ≥ 95 on auth                                        |    ☐     |
| 6     | Dashboard counts match data; works without Redis; empty states present                                            |    ☐     |
| 7     | No bare spinners; empty/error states everywhere; 360 px viewport clean; toast on every mutation                   |    ☐     |
| 8     | Backend coverage ≥ 80%; frontend ≥ 70%; Playwright golden path green in CI                                        |    ☐     |
| 9     | Live URL signs up + creates project + creates task; `/health` 200; Sentry receives test error; rollback rehearsed |    ☐     |

---

## 29. Debugging & Troubleshooting Guide

### 29.1 FastAPI / SQLAlchemy

| Symptom                                      | Diagnosis                          | Fix                                                             |
| -------------------------------------------- | ---------------------------------- | --------------------------------------------------------------- |
| `MissingGreenlet: greenlet_spawn`            | Sync ORM call inside async context | Replace `.query(...)` with `await session.execute(select(...))` |
| `InvalidRequestError: instance is not bound` | Detached instance after commit     | Set `expire_on_commit=False` on session factory                 |
| Migrations show empty diff                   | Models not imported in `env.py`    | Import `app.models` in `alembic/env.py`                         |
| `ConnectionRefusedError` on boot             | PG not up / wrong port             | `docker compose ps`; check `DATABASE_URL`                       |
| 422 on simple bodies                         | `extra="forbid"` + unknown field   | Inspect response `details.fields`                               |

### 29.2 JWT / Auth

| Symptom                                         | Diagnosis                                 | Fix                                     |
| ----------------------------------------------- | ----------------------------------------- | --------------------------------------- |
| Infinite 401 loop on frontend                   | Interceptor retries without `_retry` flag | Add `if (err.config._retry) throw err;` |
| `JWSSignatureError`                             | Wrong secret loaded                       | Verify `JWT_SECRET` in env; restart     |
| `signature has expired` immediately after issue | Clock drift                               | Sync NTP on host; leeway 30s            |
| Refresh cookie not received                     | `withCredentials: false` on axios         | Set `withCredentials: true` on instance |
| Refresh cookie not sent                         | Cross-origin / port mismatch              | Use Vite proxy in dev                   |

### 29.3 CORS

| Symptom                                       | Diagnosis                           | Fix                                                  |
| --------------------------------------------- | ----------------------------------- | ---------------------------------------------------- |
| "CORS policy: No Access-Control-Allow-Origin" | Frontend URL not in `FRONTEND_URLS` | Add exact origin (no trailing slash)                 |
| Preflight 400 / 405                           | `OPTIONS` method missing            | `CORSMiddleware` covers it — verify middleware order |
| Cookies blocked                               | `allow_credentials=False`           | Set `True`, narrow `allow_origins` (no `*`)          |

### 29.4 Alembic

| Symptom                             | Diagnosis                       | Fix                                                             |
| ----------------------------------- | ------------------------------- | --------------------------------------------------------------- |
| Autogenerate empty                  | Metadata not loaded             | `from app.db.base import Base; target_metadata = Base.metadata` |
| Constraint name drift               | Default naming                  | Use `NAMING_CONVENTION` (cf. §18.1)                             |
| Duplicate enum on rerun             | Drop with enum still referenced | `op.execute("DROP TYPE IF EXISTS …")` in downgrade              |
| `Target database is not up to date` | Mismatch                        | `alembic current` vs `alembic heads`; `alembic upgrade head`    |

### 29.5 PostgreSQL

| Symptom                           | Fix                                            |
| --------------------------------- | ---------------------------------------------- |
| `password authentication failed`  | Confirm Docker container env vars match `.env` |
| Connection drops in long sessions | `pool_pre_ping=True`                           |
| Slow query                        | `EXPLAIN ANALYZE`; add partial index           |
| `too many connections`            | Lower pool size; restart pgbouncer if used     |

### 29.6 Railway

| Symptom                     | Fix                                                                           |
| --------------------------- | ----------------------------------------------------------------------------- |
| Build OOM                   | Lower workers; smaller deps; check `pnpm install` not pulling devDeps in prod |
| Migration fails on deploy   | `railway logs --service api` — read alembic output; fix locally; redeploy     |
| 502 from web                | `pnpm preview` not bound to `$PORT`; use `-l $PORT --host`                    |
| Env var changes not applied | Service restart required after var change                                     |
| Domain not resolving        | TLS provisioning takes minutes; check Railway dashboard                       |

### 29.7 Frontend

| Symptom                     | Fix                                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Vite HMR not reloading      | Disable browser extensions; check `vite.config.ts` watch ignores                                             |
| `useQuery` infinite refetch | Stable `queryKey`; don't pass new object each render                                                         |
| Tailwind class missing      | `content` glob in `tailwind.config.ts` covers files                                                          |
| Hydration mismatch          | We're CSR (Vite) — likely date/timezone diff between SSR build and runtime; remove SSR if accidentally added |
| Build error TS5023          | Stale `node_modules`; `rm -rf node_modules && pnpm install`                                                  |

### 29.8 Diagnosis Flow (general)

1. **Reproduce** locally if possible; if not, capture `request_id`.
2. **Read logs** filtered by `request_id`.
3. **Form a hypothesis** — one variable at a time.
4. **Add a test** that fails before the fix.
5. **Fix; ensure test green**.
6. **Document** in an ADR or runbook if non-obvious.

---

## 30. Final Production Checklist

> **Run this checklist before flipping the production DNS / before declaring "live".**

### Security

- [ ] `JWT_SECRET` and `JWT_REFRESH_SECRET` are unique 48-byte random values.
- [ ] `bcrypt` cost = 12 (or higher per benchmark).
- [ ] `DOCS_ENABLED=false` in production.
- [ ] `FRONTEND_URLS` is an exact list (no `*`).
- [ ] HSTS, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` headers verified.
- [ ] Rate limiting active on `/v1/auth/*` and globally.
- [ ] Refresh-token reuse detection verified by manual test.
- [ ] `pip-audit` + `pnpm audit` clean.
- [ ] No `dangerouslySetInnerHTML` in frontend.
- [ ] Sentry capturing both ends; PII scrubbing enabled.

### Mobile / Accessibility

- [ ] 360 × 640 viewport renders cleanly.
- [ ] Touch targets ≥ 44 × 44.
- [ ] Tab order verified on every form.
- [ ] axe-core: zero critical.
- [ ] Tested on iOS Safari + Android Chrome.

### Lighthouse

- [ ] Performance ≥ 90 (Dashboard, Projects, Tasks).
- [ ] Accessibility ≥ 95.
- [ ] Best Practices ≥ 90.
- [ ] SEO ≥ 80.

### API

- [ ] OpenAPI exported + committed (`apps/api/openapi.json`).
- [ ] Every endpoint has `response_model`.
- [ ] All errors conform to envelope schema.
- [ ] Pagination capped at `size=100`.
- [ ] Idempotency-Key honored on POST mutations creating resources.

### Errors

- [ ] Frontend ErrorBoundary surfaces request-id.
- [ ] 4xx never logged at ERROR.
- [ ] 5xx triggers Sentry alert.
- [ ] User-facing errors are friendly + include request-id.

### Database / Migrations

- [ ] `alembic upgrade head` runs cleanly on fresh DB.
- [ ] Migration runs as part of Railway deploy command.
- [ ] Failed migration halts deploy (rehearsed once).
- [ ] Daily snapshots verified; one restore drill completed.
- [ ] Indexes match spec §9.3.

### Railway Deployment

- [ ] `api` and `web` services deploy from `main`.
- [ ] All env vars from spec §22 set.
- [ ] Custom domain + TLS active.
- [ ] Health check `/v1/health` responding < 5 s.
- [ ] Rollback procedure documented in `docs/runbooks/rollback.md` and rehearsed.

### Environment

- [ ] `ENVIRONMENT=production`.
- [ ] `DATABASE_URL` uses `+asyncpg`.
- [ ] `FRONTEND_URLS` matches deployed origin.
- [ ] No `.env` files in container images.

### Monitoring / Observability

- [ ] JSON logs in Railway.
- [ ] Every request has `request_id`.
- [ ] No PII in any log line (verified by test).
- [ ] 5xx-rate alert configured (`> 1% for 5 min → notify`).
- [ ] Synthetic ping on `/v1/health` (Railway or external).

### Final Sanity

- [ ] Full smoke test on production: signup → create project → invite (use 2 accounts) → create task → mark done → see in dashboard.
- [ ] README updated with live URL + demo credentials.
- [ ] CHANGELOG entry for `v1.0.0`.
- [ ] Git tag `v1.0.0` pushed.
- [ ] Project marked "shipped" 🚢 (the only emoji allowed in this document).

---

> **End of Architecture · v1.0.0**
> _This is a working document. Update commit tables, runbooks, and the production checklist as the system evolves. Every meaningful architectural deviation must land alongside a new ADR in `docs/adr/`._
