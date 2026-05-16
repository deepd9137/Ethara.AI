# SPECIFICATION — Team Task Manager (Full-Stack)

> **Status:** Implementation-ready
> **Version:** 1.0.0
> **Owner:** Engineering
> **Stack:** FastAPI · SQLAlchemy 2.0 · PostgreSQL · React · Vite · TypeScript · Railway
> **Target environment:** Production (Railway), with parity Docker-Compose for local dev

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Product Vision](#2-product-vision)
3. [Core Features](#3-core-features)
4. [User Roles & RBAC](#4-user-roles--rbac)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Recommended Tech Stack](#7-recommended-tech-stack)
8. [High-Level Architecture](#8-high-level-architecture)
9. [Database Design](#9-database-design)
10. [API Design](#10-api-design)
11. [Backend Business Logic](#11-backend-business-logic)
12. [FastAPI Backend Architecture](#12-fastapi-backend-architecture)
13. [Frontend Architecture](#13-frontend-architecture)
14. [UI/UX Guidelines](#14-uiux-guidelines)
15. [Validation Rules](#15-validation-rules)
16. [Error Handling Standards](#16-error-handling-standards)
17. [Security Best Practices](#17-security-best-practices)
18. [Performance Optimization](#18-performance-optimization)
19. [Testing Strategy](#19-testing-strategy)
20. [Logging & Monitoring](#20-logging--monitoring)
21. [Deployment Guide (Railway)](#21-deployment-guide-railway)
22. [Environment Variables](#22-environment-variables)
23. [Git Workflow](#23-git-workflow)
24. [Code Style & Engineering Rules](#24-code-style--engineering-rules)
25. [Commands Cheat Sheet](#25-commands-cheat-sheet)
26. [Edge Cases & Critical Rules](#26-edge-cases--critical-rules)
27. [Acceptance Criteria](#27-acceptance-criteria)
28. [README Structure](#28-readme-structure)
29. [Development Phases](#29-development-phases)
30. [Suggested Folder Structure](#30-suggested-folder-structure)
31. [Python Environment & Tooling Setup](#31-python-environment--tooling-setup)
32. [Production Checklist](#32-production-checklist)

---

## 1. Problem Statement

### 1.1 The Problem

Modern software, design, and operations teams coordinate work across **chat threads, spreadsheets, email, and ad-hoc tickets**. This fragmentation produces predictable, expensive failures:

- **Lost context** — decisions buried in chat, untraceable to deliverables.
- **Invisible ownership** — "who is doing this?" becomes a recurring meeting topic.
- **No single source of truth** — task status diverges between tools.
- **Weak access control** — sensitive projects (HR, finance, M&A) leak via overbroad sharing.
- **No audit trail** — compliance, incident postmortems, and personnel reviews lack defensible history.

The **Team Task Manager** is a focused, opinionated tool for **project-scoped task coordination** with **explicit role-based access control** and a **full audit trail**.

### 1.2 Target Users

| Persona | Role | Primary Goals |
|---|---|---|
| **Project Lead / Manager** | Admin | Create projects, set scope, invite contributors, monitor progress, generate status reports |
| **Individual Contributor** | Member | See assigned tasks, update status, comment, log progress |
| **Cross-functional Stakeholder** | Member (read-mostly) | Visibility into team progress without editing rights on others' work |
| **Compliance / Operations** | Admin (audit) | Use ActivityLog to demonstrate governance |

### 1.3 Collaboration Problems Solved

- Replaces "Who owns this?" with **assignee + status visible on every task**.
- Replaces "What changed?" with an immutable **ActivityLog**.
- Replaces "Can they see this?" with **RBAC enforced at the API layer**, not the UI layer.
- Replaces "Where do I even start?" with a **per-user dashboard** of *my open / overdue / due-soon* work.

### 1.4 Why RBAC Matters

Role-based access control is not a nice-to-have for a multi-tenant collaboration tool — it is the **trust boundary**:

- **Confidentiality**: a member of Project A must not enumerate Project B's tasks.
- **Integrity**: a Member cannot escalate themselves to Admin or remove the project owner.
- **Auditability**: every privileged action is attributable to a specific user.
- **Compliance posture**: aligns with SOC 2 CC6.x (logical access controls) and ISO 27001 A.9.

### 1.5 Real-World Business Use Cases

- **Software engineering team** tracking sprint deliverables across services.
- **Marketing agency** managing client campaigns with restricted per-client projects.
- **Operations / IT helpdesk** triaging incoming requests as tasks.
- **Product launch programs** coordinating cross-team milestones.
- **Compliance audits** demanding evidence of who-did-what-when.

### 1.6 Expected Scale (Year-1 Target)

| Dimension | Target | Reasoning |
|---|---|---|
| Concurrent users | 500 | Suffices for SMB / mid-market teams |
| Projects per tenant | 10,000 | Large agencies / enterprises |
| Tasks per project | 50,000 | Hot upper bound; pagination + indexes required |
| API p95 latency | < 200 ms | Industry-standard responsive UX |
| Throughput | 200 req/s sustained | One Railway service vertically; horizontal if needed |
| Storage growth | ~5 GB / year / 100-user tenant | PostgreSQL on Railway managed |

### 1.7 Productivity Challenges Addressed

1. **Cognitive load** — single screen shows everything a user owns.
2. **Status drift** — explicit state machine (`todo → in_progress → in_review → done`).
3. **Hand-offs** — assignee reassignment is one click and logged.
4. **Onboarding** — new joiners can read the ActivityLog to learn project history.
5. **Reporting** — dashboards remove the need for manual status meetings.

---

## 2. Product Vision

### 2.1 MVP Goals (Ship in 4–6 Weeks)

1. Email/password authentication with refresh-token rotation.
2. Project CRUD with hard ownership semantics.
3. Email-based invitations to existing users with **Admin / Member** roles.
4. Task CRUD with status, priority, assignee, due date.
5. Per-user dashboard: open tasks, overdue, by-status counts.
6. ActivityLog for every mutation.
7. Mobile-responsive UI down to 360 px.
8. One-command production deploy on Railway.

### 2.2 Future Scalability Goals (Post-MVP)

- **Notifications**: in-app + email (SES/Postmark) via background worker.
- **Real-time updates**: WebSocket or SSE for live task status.
- **OAuth providers**: Google, Microsoft, GitHub SSO.
- **Comments & attachments** on tasks (S3-backed).
- **Workspaces / Organizations** as a tenancy layer above Projects.
- **Custom fields & saved filters**.
- **Public REST + GraphQL API** with API keys.
- **Read replicas** for analytics queries.

### 2.3 UX Principles

| Principle | Manifestation |
|---|---|
| **Clarity over cleverness** | No hidden gestures; visible affordances |
| **Optimistic UI** | Mutations feel instant via TanStack Query optimistic updates |
| **Forgiving** | Confirm-destructive-actions, undo on soft-deletes |
| **Keyboard-first** | All primary actions reachable via shortcuts (`c` create, `/` search, `g d` go to dashboard) |
| **Empty states teach** | Every empty list explains what to do next |
| **No spinners > 300 ms without skeletons** | Perceived performance |

### 2.4 Performance Goals

| Metric | Target |
|---|---|
| API p50 latency | < 80 ms |
| API p95 latency | < 200 ms |
| API p99 latency | < 500 ms |
| LCP (mobile) | < 2.5 s |
| CLS | < 0.1 |
| TBT | < 200 ms |
| Bundle size (initial JS, gzipped) | < 200 KB |
| Lighthouse Performance | ≥ 90 |

### 2.5 Security Goals

- Zero plaintext credentials at rest or in logs.
- All authenticated endpoints enforce **(authentication + authorization)** via FastAPI dependencies.
- Refresh tokens **rotated** on every use; re-use detection invalidates the family.
- All inputs validated with Pydantic v2; outputs serialized through explicit response schemas.
- Strict CORS allow-list (no wildcard in production).
- TLS terminated at Railway edge; HSTS enforced.

### 2.6 Developer Experience Goals

- **One-command bootstrap** (`make bootstrap` or `pnpm setup`).
- **Hot reload** on both ends.
- **Typed API contracts** end-to-end (Pydantic → OpenAPI → generated TS client OR Zod mirror).
- **CI < 5 minutes** for the typical PR.
- **Pre-commit hooks** for ruff/black/mypy/eslint/prettier.

### 2.7 Maintainability Goals

- **Clean separation**: routes → services → repositories → models. No business logic in routes.
- **No raw SQL** in routes; all DB access through repositories.
- **No `any`** in TypeScript; no untyped Python functions.
- **Documented decisions**: ADRs under `docs/adr/`.
- **Test coverage**: ≥ 80% backend line coverage; ≥ 70% frontend statement coverage.

---

## 3. Core Features

### 3.1 Authentication

**Description.** Email + password authentication with JWT access tokens and rotating refresh tokens.

**Business logic.**
- Sign-up creates a `User` row; password is bcrypt-hashed with cost factor 12.
- Login issues a short-lived **access token** (15 min) and a long-lived **refresh token** (14 days).
- Refresh tokens are stored hashed in `refresh_tokens` table (`jti`, `user_id`, `family_id`, `expires_at`, `revoked_at`).
- Refresh rotates the token: previous token is marked used; a new token replaces it.
- **Re-use detection**: if a previously-used refresh token is presented, the entire family is revoked (suspected theft).

**User flow.**
1. User signs up → automatically logged in.
2. Access token kept **in memory** (Zustand store).
3. Refresh token stored in **HttpOnly, Secure, SameSite=Strict cookie**.
4. Axios interceptor on 401 → call `/auth/refresh` → retry once.
5. Logout → server revokes refresh token; client clears in-memory state.

**Validation rules.**
- Email: RFC 5322 syntax, max 254 chars, normalized lowercase.
- Password: min 12 chars, must include letter + digit; max 128 chars.
- Name: 1–80 chars, trimmed.

**Permissions.** Unauthenticated for signup/login/refresh; authenticated for `/auth/me` and `/auth/logout`.

**API behavior.** See [Section 10](#10-api-design).

**Failure handling.**
- Wrong password → generic `INVALID_CREDENTIALS` (no enumeration).
- Locked account → `ACCOUNT_LOCKED` after 10 failed attempts in 15 minutes.
- Expired refresh → `REFRESH_EXPIRED` → client redirects to `/login`.

**Edge cases.**
- Concurrent refresh requests from two tabs → race-safe via DB unique constraint on `(family_id, used_at IS NULL)`.
- Clock skew → tokens validated with 30-second leeway.
- User changes password → all refresh families revoked.

**Security considerations.**
- bcrypt rounds tunable via env var.
- Constant-time comparison for credentials and tokens.
- No password in logs (Pydantic `SecretStr`).

---

### 3.2 Project Management

**Description.** Authenticated users create, list, view, update, and soft-delete projects they own or belong to.

**Business logic.**
- The creator is automatically inserted into `project_members` with role `ADMIN`.
- A project must have ≥ 1 Admin at all times; demoting/removing the last Admin fails.
- Soft delete sets `deleted_at`; project becomes invisible to all but excluded from listings, including for the owner. Hard delete is reserved for backend cleanup jobs.

**User flow.** Create → see in sidebar → open → invite members → create tasks.

**Validation rules.**
- Name: 2–80 chars, unique per `(owner_id, deleted_at IS NULL)`.
- Description: max 2,000 chars, plaintext (no HTML).
- Slug: auto-derived from name, lowercase, dash-separated.

**Permissions.**
- Create: any authenticated user.
- Read: members only.
- Update / Soft-delete: Admins only.
- Transfer ownership: current owner only.

**API behavior.** `POST /projects`, `GET /projects`, `GET /projects/{id}`, `PATCH /projects/{id}`, `DELETE /projects/{id}`.

**Failure handling.**
- Duplicate name → `409 PROJECT_NAME_TAKEN`.
- Non-member access → `404` (not `403`, to avoid leaking existence).

**Edge cases.**
- User deactivated while owning projects → projects remain readable to other members; system role `ORPHANED` flag set.
- Soft-deleted project restoration → admin-only, within 30 days, restores associations.

**Security considerations.** Authorization enforced server-side; UI hides controls but is **not** the trust boundary.

---

### 3.3 Team Management

**Description.** Admins invite existing users (by email) to a project as Admin or Member; manage roles; remove members.

**Business logic.**
- Invitation looks up the user by normalized email.
  - If found, immediately creates `project_members` row with `status='active'`.
  - If not found, creates a `pending_invitation` (MVP: out of scope — see post-MVP).
- The owner cannot be removed; ownership must be transferred first.
- Removing a member nullifies (but does not delete) their `Task.assignee_id`; tasks become unassigned.

**User flow.** Admin opens Members tab → enters email → selects role → submits → user appears in list with role badge.

**Validation rules.**
- Email format; cannot invite self; cannot invite an already-present member.
- Role must be in `{ADMIN, MEMBER}`.

**Permissions.** Admin only for all mutations; both roles can list members.

**API behavior.** `POST /projects/{id}/members`, `GET /projects/{id}/members`, `PATCH /projects/{id}/members/{user_id}`, `DELETE /projects/{id}/members/{user_id}`.

**Failure handling.**
- Inviting non-existent user (MVP) → `404 USER_NOT_FOUND`.
- Inviting duplicate member → `409 ALREADY_MEMBER`.
- Demoting last Admin → `409 LAST_ADMIN`.

**Edge cases.**
- Mass invite with one invalid email → entire request rejected (atomic).
- User removed from project while having an open task assignment → assignee nulled, ActivityLog entry written.

**Security considerations.** Email enumeration mitigated by returning the same error for "user exists / does not exist" in the *signup* path, not membership (members are intentionally enumerable to Admins).

---

### 3.4 Task Management

**Description.** Members create, read, update, and soft-delete tasks within projects they belong to.

**Business logic.**
- A Task belongs to exactly one Project.
- Fields: `title`, `description`, `status`, `priority`, `assignee_id`, `due_date`, `completed_at`.
- **Status FSM**: `todo → in_progress → in_review → done`. Transitions only along this DAG plus `done → in_review` (reopen). Arbitrary jumps are rejected.
- `completed_at` is auto-set when status → `done` and nulled on reopen.
- `assignee_id` must reference an active project member.

**User flow.** Open project → click "+ New Task" → fill form → save → task appears in list and on assignee's dashboard.

**Validation rules.**
- Title: 2–140 chars.
- Description: max 10,000 chars.
- Due date: must be ≥ today (allow today). Optional.
- Priority: `low | medium | high | critical`. Default `medium`.

**Permissions.**
- Create: any project member.
- Update title/desc/priority/due/assignee: Admins, or the task's creator, or the current assignee.
- Update status: any project member.
- Delete (soft): Admins, or the task's creator.

**API behavior.** `POST /projects/{id}/tasks`, `GET /projects/{id}/tasks?status=&assignee=&priority=&due_before=&q=&page=&size=&sort=`, `GET /tasks/{id}`, `PATCH /tasks/{id}`, `PATCH /tasks/{id}/status`, `DELETE /tasks/{id}`.

**Failure handling.**
- Invalid status transition → `422 INVALID_TASK_TRANSITION` with `allowed` list.
- Assignee not a member → `422 ASSIGNEE_NOT_MEMBER`.

**Edge cases.**
- Assignee removed from project → on next read, frontend shows "Unassigned"; backend already nulled.
- Concurrent edits → optimistic concurrency via `updated_at` `If-Unmodified-Since` semantics or `version` integer (MVP: `If-Match: <updated_at_iso>`).

**Security considerations.** Project membership re-verified on every task operation; no implicit trust from client-supplied `project_id`.

---

### 3.5 Dashboard & Analytics

**Description.** Per-user aggregate view: open tasks, overdue, due-this-week, by-status counts, recent activity.

**Business logic.**
- All counts respect RBAC (only tasks in projects the user belongs to).
- Aggregations performed via SQL `GROUP BY` (no per-task fetching in Python).
- Optional Redis cache (60-second TTL) keyed by `user_id`.

**User flow.** Login → land on `/dashboard` → see widgets → click any widget to drill into a filtered task list.

**API behavior.** `GET /dashboard/stats`, `GET /dashboard/my-tasks`, `GET /dashboard/recent-activity`.

**Edge cases.**
- New user with no projects → empty-state card "Create your first project".
- User in many projects → cap recent-activity to 50 most-recent entries.

---

### 3.6 Activity Logs / Audit Tracking

**Description.** Immutable, append-only log of every meaningful mutation.

**Business logic.**
- A row is written in the **same DB transaction** as the mutation (no eventual consistency hole).
- Schema: `id`, `actor_id`, `project_id`, `entity_type`, `entity_id`, `action`, `metadata JSONB`, `created_at`.
- Actions: `PROJECT_CREATED`, `PROJECT_UPDATED`, `MEMBER_INVITED`, `MEMBER_REMOVED`, `MEMBER_ROLE_CHANGED`, `TASK_CREATED`, `TASK_UPDATED`, `TASK_STATUS_CHANGED`, `TASK_ASSIGNED`, `TASK_DELETED`.
- ActivityLog rows are **never updated or deleted** via the API.

**User flow.** Admin opens project → Activity tab → paginated newest-first log.

**Permissions.** Project members can read; only system (service layer) writes.

**Edge cases.** If a mutation succeeds but log write fails, the entire transaction rolls back — no partial state.

**Security considerations.** Treat ActivityLog as the source of truth for incident forensics. Backups must include it.

---

### 3.7 Notifications (Future Enhancement)

Out of scope for MVP. Planned design:

- Event bus on `ActivityLog.insert`.
- Background worker (RQ/ARQ + Redis) drains events.
- Per-user preferences (`email`, `in_app`, `digest`).
- Email via Postmark/SES with templated transactional messages.
- In-app via WebSocket fan-out.

---

## 4. User Roles & RBAC

### 4.1 Roles

| Role | Scope | Description |
|---|---|---|
| **Admin** | Per-project | Creator or any user explicitly promoted. Manages members, edits project, deletes tasks. |
| **Member** | Per-project | Default invited role. Creates and works tasks; cannot manage members or project metadata. |

> **Note.** Roles are **project-scoped**, not global. A user may be Admin of Project A and Member of Project B simultaneously. There is no system-wide "super admin" role in the MVP.

### 4.2 Authorization Matrix

| Action | Anonymous | Authenticated (non-member) | Member | Admin |
|---|:---:|:---:|:---:|:---:|
| Sign up | ✅ | — | — | — |
| Login | ✅ | — | — | — |
| Create project | ❌ | ✅ | ✅ | ✅ |
| List own projects | ❌ | ✅ | ✅ | ✅ |
| Read project | ❌ | ❌ (404) | ✅ | ✅ |
| Update project | ❌ | ❌ | ❌ | ✅ |
| Delete project (soft) | ❌ | ❌ | ❌ | ✅ |
| List members | ❌ | ❌ | ✅ | ✅ |
| Invite member | ❌ | ❌ | ❌ | ✅ |
| Change member role | ❌ | ❌ | ❌ | ✅ |
| Remove member | ❌ | ❌ | ❌ | ✅ |
| Create task | ❌ | ❌ | ✅ | ✅ |
| Read task | ❌ | ❌ | ✅ | ✅ |
| Update task (own / assigned) | ❌ | ❌ | ✅ | ✅ |
| Update task (others') | ❌ | ❌ | ❌ | ✅ |
| Change task status | ❌ | ❌ | ✅ | ✅ |
| Delete task (soft) | ❌ | ❌ | own only | ✅ |
| Read activity log | ❌ | ❌ | ✅ | ✅ |

### 4.3 Ownership Rules

- **Project ownership** is the `User` row referenced by `Project.owner_id`. The owner is always Admin.
- Ownership transfer: `POST /projects/{id}/transfer-owner` (Admin → Admin only).
- The owner cannot be removed without first transferring ownership.

### 4.4 Invitation Rules

- Admin enters email of an **existing user**.
- Cannot invite self.
- Cannot duplicate existing membership.
- Inviter is recorded in `ActivityLog` and in `project_members.invited_by`.

### 4.5 Project Visibility Rules

- A project's existence is **not** discoverable to non-members. API returns `404` (not `403`) for non-member reads.
- Search/list endpoints filter by membership server-side; no client-side filtering.

### 4.6 Route Protection Strategy (Frontend)

- `<ProtectedRoute>` HOC: redirects unauthenticated users to `/login`, preserving intended destination via `?next=`.
- `<RequireProjectAdmin>` wraps admin-only screens; on `403` server response, redirects to `/projects/{id}` with a toast.
- Auth state hydrated from `/auth/me` on app boot.

### 4.7 API Authorization Strategy (Backend)

Three composable FastAPI dependencies:

```python
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User: ...
async def require_project_member(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProjectMember: ...
async def require_project_admin(member: ProjectMember = Depends(require_project_member)) -> ProjectMember: ...
```

- Failure of `get_current_user` → `401`.
- Failure of `require_project_member` → `404` (mask existence).
- Failure of `require_project_admin` → `403` (existence already known).

### 4.8 Access Validation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant D as Auth Dep
    participant R as RBAC Dep
    participant S as Service
    C->>M: Request + Bearer token
    M->>M: CORS, request-id, rate-limit
    M->>D: extract & verify JWT
    D-->>M: User or 401
    D->>R: project_id from path
    R->>R: query project_members
    R-->>M: ProjectMember or 404
    R->>R: assert role if admin route
    R-->>M: pass or 403
    M->>S: invoke service
    S-->>C: 200 / 201 / 4xx
```

---

## 5. Functional Requirements

### Authentication
- **FR-1** A visitor can sign up with email, name, and password.
- **FR-2** A user can log in with email and password.
- **FR-3** A logged-in user can refresh their access token via a rotating refresh token.
- **FR-4** A logged-in user can log out, revoking the current refresh token.
- **FR-5** A logged-in user can view their own profile (`/auth/me`).
- **FR-6** A logged-in user can change their password (revokes all refresh families).

### Projects
- **FR-7** An authenticated user can create a project.
- **FR-8** A project creator is automatically assigned the Admin role.
- **FR-9** A user can list projects they belong to.
- **FR-10** A project member can view project details.
- **FR-11** An Admin can edit project name and description.
- **FR-12** An Admin can soft-delete a project.
- **FR-13** A project owner can transfer ownership to another Admin.
- **FR-14** A non-member cannot determine whether a project exists.

### Members
- **FR-15** An Admin can invite an existing user by email as Admin or Member.
- **FR-16** Members can list project members and their roles.
- **FR-17** An Admin can change a member's role.
- **FR-18** An Admin can remove a member from a project.
- **FR-19** The last Admin cannot be demoted or removed.
- **FR-20** The owner cannot be removed without ownership transfer.

### Tasks
- **FR-21** A member can create a task in a project.
- **FR-22** Tasks have title, description, status, priority, assignee, due date.
- **FR-23** Status transitions follow `todo → in_progress → in_review → done`, with `done → in_review` reopen.
- **FR-24** An assignee must be an active project member at creation/update time.
- **FR-25** Members can list / filter / sort / paginate tasks.
- **FR-26** A member can update tasks they created or are assigned to.
- **FR-27** Any member can change a task's status (within FSM).
- **FR-28** Admins or task creators can soft-delete tasks.
- **FR-29** Completing a task sets `completed_at`; reopening clears it.
- **FR-30** Concurrent edits use optimistic concurrency (`If-Match`).

### Dashboard
- **FR-31** A logged-in user sees aggregate counts: open, overdue, due-this-week, by-status, by-priority.
- **FR-32** A logged-in user sees their open tasks across all projects.
- **FR-33** A logged-in user sees a recent-activity feed scoped to their projects.

### Audit
- **FR-34** Every project/member/task mutation writes one ActivityLog row in the same transaction.
- **FR-35** Members can read the activity log of their projects.
- **FR-36** ActivityLog rows are immutable via the API.

### Cross-cutting
- **FR-37** All list endpoints support cursor-or-offset pagination, sorting, and filtering.
- **FR-38** All authenticated endpoints reject expired/invalid tokens.
- **FR-39** All endpoints return standardized envelopes.
- **FR-40** All endpoints emit a correlation/request ID.
- **FR-41** All form errors are surfaced field-by-field on the frontend.
- **FR-42** All destructive UI actions require explicit confirmation.
- **FR-43** All times are stored UTC; displayed in user's local timezone.
- **FR-44** API documentation is auto-generated and accessible at `/docs` (non-production).
- **FR-45** Health endpoint `/health` returns liveness + DB connectivity.
- **FR-46** The application is fully usable on a 360 px viewport.
- **FR-47** Keyboard shortcuts cover the primary actions.
- **FR-48** All servers / browsers operate over HTTPS in production.
- **FR-49** Failed migrations halt deployment without partial schema changes.
- **FR-50** Backups of PostgreSQL are taken daily (Railway managed snapshot policy).

---

## 6. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| **Scalability** | Stateless API; horizontal scale via Railway replicas | 4 replicas supported without sticky sessions |
| **Performance** | API p95 latency | < 200 ms |
| **Performance** | DB queries per request | ≤ 5 typical, ≤ 10 hard cap |
| **Availability** | Monthly uptime | 99.9% (≤ 43 min downtime) |
| **Reliability** | Graceful degradation on Redis outage | App functions without cache |
| **Security** | OWASP Top 10 mitigations documented | All 10 addressed (Section 17) |
| **Security** | Dependency scanning | Weekly `pip-audit` + `pnpm audit` |
| **Accessibility** | WCAG 2.1 AA conformance | Verified with axe-core in CI |
| **Mobile responsiveness** | Smallest supported viewport | 360 × 640 |
| **Maintainability** | Cyclomatic complexity per function | < 10 |
| **Maintainability** | Test coverage backend | ≥ 80% lines, ≥ 70% branches |
| **Observability** | All requests have correlation IDs | 100% |
| **Observability** | Structured JSON logs | All log lines |
| **Error resilience** | Network failure → retry with backoff | TanStack Query default retry x3 |
| **Latency targets** | TTFB | < 100 ms (cached endpoints) |
| **Internationalization** | UTF-8 throughout | All endpoints, DB columns |
| **Privacy** | PII (email, name) never logged | Verified via log scrubbing |

---

## 7. Recommended Tech Stack

### 7.1 Frontend

| Tech | Why |
|---|---|
| **React 18+** | Mature ecosystem, concurrent rendering, hooks-first |
| **Vite** | Sub-second cold start, esbuild-fast HMR, first-class TS support |
| **TypeScript (strict)** | Catches contract drift at compile time; required for safe refactors |
| **TailwindCSS** | Utility-first; zero CSS naming bikeshed; consistent design tokens |
| **TanStack Query** | Server-state caching, mutations, dedupe, devtools — replaces 70% of Redux for typical apps |
| **Zustand** | Tiny (≤ 1 KB), no boilerplate; ideal for auth state and ephemeral UI flags |
| **React Router v6** | Nested routes, data loaders, type-safe path helpers |
| **Axios** | Interceptor model for auth refresh + error normalization |
| **React Hook Form** | Uncontrolled-by-default; minimal re-renders; pairs cleanly with Zod |
| **Zod** | Single source of truth for form schemas; type inference into TS |

### 7.2 Backend

| Tech | Why |
|---|---|
| **Python 3.12+** | Generics syntax, performance gains, `tomllib` stdlib |
| **FastAPI** | ASGI, automatic OpenAPI, Pydantic-native, DI built-in |
| **SQLAlchemy 2.0** | New `select()` API; full typing; async-first; mature |
| **Alembic** | Battle-tested schema migrations |
| **Pydantic v2** | 10× faster than v1; strict mode; serializers |
| **asyncpg** | Fastest PostgreSQL driver for asyncio |

### 7.3 Database

| Tech | Why |
|---|---|
| **PostgreSQL 16** | JSONB, partial indexes, generated columns, row-level security if needed |

### 7.4 Auth

- **JWT (HS256 in MVP)** — symmetric, simpler key management on Railway. Asymmetric (RS256/EdDSA) is a future migration once a KMS is introduced.
- **OAuth2PasswordBearer** — FastAPI's spec-compliant scheme; integrates with Swagger UI for in-browser testing.

### 7.5 Tooling

| Tool | Role | Why |
|---|---|---|
| **uv** | Python deps + venv | Rust-fast resolver, lockfile, reproducible builds, replaces pip/poetry/virtualenv |
| **pnpm** | Node deps | Content-addressed store; deterministic; saves disk |
| **ruff** | Linter | 10–100× faster than flake8; covers isort + pyflakes + pylint subset |
| **black** | Formatter | One canonical style; zero discussion |
| **mypy --strict** | Type checking | Catches `None` bugs, signature drift |
| **pytest + pytest-asyncio + httpx** | Tests | Async fixtures, real ASGI calls without socket |

### 7.6 Deployment

- **Railway** — minimal-config PaaS; managed PostgreSQL; per-PR preview envs; reasonable pricing; built-in metrics.

### 7.7 Why This Stack Wins

- **Scalability**: stateless API + managed Postgres = horizontal scaling trivial.
- **Developer productivity**: end-to-end types from DB → API → UI form schema.
- **Deployment**: Railway's GitHub integration turns merge → deploy into a non-event.
- **Maintainability**: opinionated stack — fewer micro-decisions, faster onboarding.

---

## 8. High-Level Architecture

### 8.1 System Architecture

```mermaid
flowchart TB
    subgraph Browser
      A[React SPA<br/>Vite Build]
    end
    subgraph "Railway Edge"
      CDN[Static Assets via Railway<br/>HTTPS / HSTS]
    end
    subgraph "Railway: API Service"
      API[FastAPI + Uvicorn]
      MW[Middleware:<br/>CORS, RequestID, RateLimit, Logging]
      ROUTER[Routers]
      SVC[Services]
      REPO[Repositories]
      API --> MW --> ROUTER --> SVC --> REPO
    end
    subgraph "Railway: Data"
      PG[(PostgreSQL 16)]
      REDIS[(Redis<br/>optional)]
    end
    A -->|REST + Bearer JWT| API
    CDN --> A
    REPO --> PG
    SVC -.->|cache| REDIS
```

### 8.2 Request Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant FE as React SPA
    participant API as FastAPI
    participant DB as PostgreSQL
    U->>FE: clicks "Create Task"
    FE->>FE: Zod validate form
    FE->>API: POST /projects/{id}/tasks (Bearer JWT)
    API->>API: Middleware: request_id, rate-limit, CORS
    API->>API: Deps: get_current_user → require_project_member
    API->>API: Service: validate payload, FSM, business rules
    API->>DB: BEGIN; INSERT task; INSERT activity_log; COMMIT
    API-->>FE: 201 + Task DTO
    FE->>FE: TanStack Query: setQueryData (optimistic) → invalidate
    FE-->>U: UI updated; toast "Task created"
```

### 8.3 Authentication Flow (JWT + Refresh Rotation)

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB
    Client->>API: POST /auth/login (email, password)
    API->>DB: SELECT user
    API->>API: bcrypt verify
    API->>DB: INSERT refresh_token (hashed, family_id, jti)
    API-->>Client: 200 { access_token } + Set-Cookie refresh (HttpOnly)
    Note over Client: access in memory; refresh in cookie

    Client->>API: GET /projects (Bearer access)
    API-->>Client: 200 / 401 if expired

    Client->>API: POST /auth/refresh (cookie)
    API->>DB: SELECT refresh by jti
    alt token unused
        API->>DB: mark used; INSERT new refresh (same family)
        API-->>Client: 200 { access_token } + Set-Cookie new refresh
    else token reused
        API->>DB: REVOKE entire family
        API-->>Client: 401 REFRESH_REUSED
    end
```

### 8.4 Database Relationships

```mermaid
erDiagram
    USER ||--o{ PROJECT : owns
    USER ||--o{ PROJECT_MEMBER : "is"
    USER ||--o{ REFRESH_TOKEN : "has"
    USER ||--o{ ACTIVITY_LOG : "performs"
    PROJECT ||--o{ PROJECT_MEMBER : "has"
    PROJECT ||--o{ TASK : "contains"
    PROJECT ||--o{ ACTIVITY_LOG : "scopes"
    USER ||--o{ TASK : "assigned (nullable)"
    USER ||--o{ TASK : "created"
    USER {
      uuid id PK
      citext email UK
      string name
      bytea password_hash
      timestamptz created_at
      timestamptz updated_at
      timestamptz deleted_at
    }
    PROJECT {
      uuid id PK
      uuid owner_id FK
      string name
      text description
      timestamptz created_at
      timestamptz updated_at
      timestamptz deleted_at
    }
    PROJECT_MEMBER {
      uuid id PK
      uuid project_id FK
      uuid user_id FK
      enum role
      uuid invited_by FK
      timestamptz created_at
    }
    TASK {
      uuid id PK
      uuid project_id FK
      uuid creator_id FK
      uuid assignee_id FK "nullable"
      string title
      text description
      enum status
      enum priority
      date due_date "nullable"
      timestamptz completed_at "nullable"
      timestamptz created_at
      timestamptz updated_at
      timestamptz deleted_at
    }
    ACTIVITY_LOG {
      uuid id PK
      uuid actor_id FK
      uuid project_id FK
      string entity_type
      uuid entity_id
      string action
      jsonb metadata
      timestamptz created_at
    }
```

### 8.5 Deployment Flow

```mermaid
flowchart LR
    DEV[Developer push] --> GH[GitHub]
    GH -->|main branch| RW[Railway: Build]
    RW --> MIG[Run Alembic upgrade head]
    MIG -->|success| DEP[Deploy api + web services]
    MIG -->|failure| HALT[Halt + alert]
    DEP --> HC[Health check /health]
    HC -->|ok| LIVE[Live]
    HC -->|fail x3| RB[Auto-rollback]
```

---

## 9. Database Design

### 9.1 Conventions

- **PKs**: `UUID` (`gen_random_uuid()` via `pgcrypto`); never natural keys.
- **Timestamps**: every table has `created_at`, `updated_at` (`onupdate=func.now()`), both `TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **Soft deletes**: `deleted_at TIMESTAMPTZ NULL`. Repositories filter `WHERE deleted_at IS NULL` by default; explicit `include_deleted=True` available for admin tooling.
- **Enums**: defined as PostgreSQL `ENUM` types + Python `enum.StrEnum`. Migrations create them in dedicated revisions to allow safe value additions.
- **Foreign keys**: explicit `ON DELETE` semantics — never default. Most are `ON DELETE RESTRICT`; ActivityLog uses `ON DELETE SET NULL` so logs persist after user soft-delete.
- **No `NULL` strings**: empty optional text uses `''`, nullable means "intentionally not set".

### 9.2 Table Schemas

```sql
-- USERS
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           CITEXT NOT NULL UNIQUE,
  name            VARCHAR(80) NOT NULL,
  password_hash   BYTEA NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_users_active ON users (id) WHERE deleted_at IS NULL;

-- PROJECTS
CREATE TABLE projects (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  name            VARCHAR(80) NOT NULL,
  description     TEXT NOT NULL DEFAULT '',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ,
  CONSTRAINT projects_name_per_owner_uq
    UNIQUE NULLS NOT DISTINCT (owner_id, name, deleted_at)
);
CREATE INDEX idx_projects_owner_alive ON projects (owner_id) WHERE deleted_at IS NULL;

-- PROJECT_MEMBERS
CREATE TYPE project_role AS ENUM ('admin', 'member');
CREATE TABLE project_members (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
  role            project_role NOT NULL,
  invited_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT project_members_unique_pair UNIQUE (project_id, user_id)
);
CREATE INDEX idx_pm_user ON project_members (user_id);
CREATE INDEX idx_pm_project ON project_members (project_id);

-- TASKS
CREATE TYPE task_status   AS ENUM ('todo', 'in_progress', 'in_review', 'done');
CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TABLE tasks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  creator_id      UUID NOT NULL REFERENCES users(id)    ON DELETE RESTRICT,
  assignee_id     UUID REFERENCES users(id)             ON DELETE SET NULL,
  title           VARCHAR(140) NOT NULL,
  description     TEXT NOT NULL DEFAULT '',
  status          task_status   NOT NULL DEFAULT 'todo',
  priority        task_priority NOT NULL DEFAULT 'medium',
  due_date        DATE,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ,
  CONSTRAINT tasks_title_len CHECK (char_length(title) BETWEEN 2 AND 140)
);
CREATE INDEX idx_tasks_project_alive ON tasks (project_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_assignee_open ON tasks (assignee_id) WHERE deleted_at IS NULL AND status <> 'done';
CREATE INDEX idx_tasks_status         ON tasks (status);
CREATE INDEX idx_tasks_due_date       ON tasks (due_date) WHERE due_date IS NOT NULL AND status <> 'done';

-- REFRESH_TOKENS
CREATE TABLE refresh_tokens (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  family_id       UUID NOT NULL,
  token_hash      BYTEA NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  used_at         TIMESTAMPTZ,
  revoked_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT refresh_tokens_hash_uq UNIQUE (token_hash)
);
CREATE INDEX idx_refresh_user_alive ON refresh_tokens (user_id) WHERE revoked_at IS NULL;

-- ACTIVITY_LOG
CREATE TABLE activity_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id        UUID REFERENCES users(id) ON DELETE SET NULL,
  project_id      UUID REFERENCES projects(id) ON DELETE SET NULL,
  entity_type     VARCHAR(32) NOT NULL,
  entity_id       UUID NOT NULL,
  action          VARCHAR(48) NOT NULL,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_activity_project_created ON activity_logs (project_id, created_at DESC);
CREATE INDEX idx_activity_actor           ON activity_logs (actor_id);
```

### 9.3 Indexing Strategy

| Query pattern | Index |
|---|---|
| "My tasks across projects" | `idx_tasks_assignee_open` (partial) |
| "Tasks in project, filter by status" | `idx_tasks_project_alive` + `idx_tasks_status` |
| "Overdue tasks" | `idx_tasks_due_date` (partial: not done) |
| "Project activity feed" | `idx_activity_project_created` |
| "Refresh token lookup" | `refresh_tokens_hash_uq` |
| "Is user a member?" | `project_members_unique_pair` |

Partial indexes used aggressively to shrink hot indexes and skip soft-deleted rows.

### 9.4 Cascade Rules Summary

| FK | On Delete | Why |
|---|---|---|
| `project_members.project_id → projects` | `CASCADE` | Membership meaningless without project |
| `project_members.user_id → users` | `CASCADE` | User gone, membership gone |
| `tasks.project_id → projects` | `RESTRICT` | Soft-delete projects, never hard |
| `tasks.assignee_id → users` | `SET NULL` | Don't orphan; show "Unassigned" |
| `tasks.creator_id → users` | `RESTRICT` | Audit anchor |
| `refresh_tokens.user_id → users` | `CASCADE` | Tokens worthless after user deletion |
| `activity_logs.actor_id → users` | `SET NULL` | Preserve audit history |
| `activity_logs.project_id → projects` | `SET NULL` | Preserve audit history |

---

## 10. API Design

### 10.1 Conventions

- **Base URL**: `https://api.example.com/v1`
- **Auth**: `Authorization: Bearer <access_token>`
- **Content-type**: `application/json; charset=utf-8`
- **Time format**: ISO-8601 UTC (`2026-01-15T10:00:00Z`)
- **IDs**: UUID v4 strings
- **Pagination**: offset-based for MVP (`?page=1&size=20`); cursor migration documented in ADR-0002
- **Sorting**: `?sort=created_at,-priority` (prefix `-` = desc)
- **Filtering**: explicit query params per resource; no JSON filter DSL
- **Idempotency**: `Idempotency-Key` header honored on `POST` mutations creating resources
- **Concurrency**: `If-Match: <updated_at_iso>` on `PATCH`/`PUT` resource endpoints

### 10.2 Standard Response Envelope

**Success:**
```json
{
  "success": true,
  "data": { "...": "..." },
  "meta": { "request_id": "req_01J...", "page": 1, "size": 20, "total": 142 }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task does not exist or you do not have access",
    "details": { "task_id": "..." }
  },
  "meta": { "request_id": "req_01J..." }
}
```

### 10.3 Endpoints

#### Auth

| Method | Path | Auth | Description | Body | Success | Errors |
|---|---|:---:|---|---|---|---|
| POST | `/auth/signup` | — | Register | `{email, name, password}` | `201` user+tokens | `409 EMAIL_TAKEN`, `422` |
| POST | `/auth/login` | — | Log in | `{email, password}` | `200` tokens | `401 INVALID_CREDENTIALS`, `423 ACCOUNT_LOCKED` |
| POST | `/auth/refresh` | cookie | Rotate token | — | `200` new tokens | `401 REFRESH_EXPIRED`, `401 REFRESH_REUSED` |
| POST | `/auth/logout` | ✅ | Revoke refresh | — | `204` | `401` |
| GET  | `/auth/me` | ✅ | Current user | — | `200` user | `401` |
| POST | `/auth/change-password` | ✅ | Change password | `{current, new}` | `204` | `401 BAD_CURRENT`, `422` |

#### Projects

| Method | Path | Auth | Role | Description |
|---|---|:---:|:---:|---|
| POST   | `/projects` | ✅ | any | Create |
| GET    | `/projects?page=&size=&sort=&q=` | ✅ | member | List my projects |
| GET    | `/projects/{id}` | ✅ | member | Read |
| PATCH  | `/projects/{id}` | ✅ | admin | Update |
| DELETE | `/projects/{id}` | ✅ | admin | Soft delete |
| POST   | `/projects/{id}/transfer-owner` | ✅ | owner | Transfer ownership |

#### Members

| Method | Path | Auth | Role | Description |
|---|---|:---:|:---:|---|
| POST   | `/projects/{id}/members` | ✅ | admin | Invite |
| GET    | `/projects/{id}/members` | ✅ | member | List |
| PATCH  | `/projects/{id}/members/{user_id}` | ✅ | admin | Change role |
| DELETE | `/projects/{id}/members/{user_id}` | ✅ | admin | Remove |

#### Tasks

| Method | Path | Auth | Role | Description |
|---|---|:---:|:---:|---|
| POST   | `/projects/{id}/tasks` | ✅ | member | Create |
| GET    | `/projects/{id}/tasks?status=&assignee_id=&priority=&due_before=&q=&page=&size=&sort=` | ✅ | member | List in project |
| GET    | `/tasks/{id}` | ✅ | member | Read |
| PATCH  | `/tasks/{id}` | ✅ | member* | Update fields |
| PATCH  | `/tasks/{id}/status` | ✅ | member | Status FSM transition |
| DELETE | `/tasks/{id}` | ✅ | admin/creator | Soft delete |

\* Member must be creator or current assignee for non-status fields.

#### Dashboard

| Method | Path | Auth | Description |
|---|---|:---:|---|
| GET | `/dashboard/stats` | ✅ | Counts: open, overdue, by-status, by-priority |
| GET | `/dashboard/my-tasks?status=&due_before=` | ✅ | Assigned-to-me across projects |
| GET | `/dashboard/recent-activity?limit=50` | ✅ | Activity across my projects |

#### System

| Method | Path | Auth | Description |
|---|---|:---:|---|
| GET | `/health` | — | Liveness + DB ping; returns `{status, db, version, commit}` |
| GET | `/docs` | — | OpenAPI Swagger UI (non-prod only) |
| GET | `/openapi.json` | — | OpenAPI 3.1 spec |

### 10.4 Status Code Standards

| Code | Use |
|---|---|
| `200 OK` | Successful read or update |
| `201 Created` | Resource created |
| `204 No Content` | Successful with no body (delete, logout) |
| `400 Bad Request` | Malformed payload |
| `401 Unauthorized` | Missing/invalid token |
| `403 Forbidden` | Authenticated but role insufficient (membership confirmed) |
| `404 Not Found` | Resource absent OR caller has no access |
| `409 Conflict` | Unique violation, FSM violation, last-admin |
| `422 Unprocessable Entity` | Field validation |
| `423 Locked` | Account lockout |
| `429 Too Many Requests` | Rate limit hit |
| `500 Internal Server Error` | Unhandled; sentry-tracked |

### 10.5 Error Code Catalog (excerpt)

```
EMAIL_TAKEN, INVALID_CREDENTIALS, ACCOUNT_LOCKED, REFRESH_EXPIRED, REFRESH_REUSED,
PROJECT_NOT_FOUND, PROJECT_NAME_TAKEN,
MEMBER_NOT_FOUND, ALREADY_MEMBER, LAST_ADMIN, CANNOT_REMOVE_OWNER,
TASK_NOT_FOUND, INVALID_TASK_TRANSITION, ASSIGNEE_NOT_MEMBER,
VALIDATION_FAILED, RATE_LIMITED, INTERNAL_ERROR
```

---

## 11. Backend Business Logic

### 11.1 Service Layer

- One service module per aggregate: `auth_service.py`, `project_service.py`, `member_service.py`, `task_service.py`, `dashboard_service.py`, `activity_service.py`.
- Services are stateless functions/classes that take `(repos, current_user, payload)`.
- Services own all business rules — never in routers, never in repositories.
- Services may compose other services within the same transaction.

### 11.2 Repository Pattern

- One repo per model: `users_repo`, `projects_repo`, `tasks_repo`, etc.
- Repositories return ORM models or DTOs; never `dict`.
- Repositories must not contain business logic — only SQL/ORM operations.
- Each method takes `(db: AsyncSession, ...)`.

### 11.3 Dependency Injection

- All cross-cutting concerns provided via FastAPI `Depends`:
  - `get_db` — yields `AsyncSession`, commits on success, rolls back on exception.
  - `get_current_user`, `require_project_member`, `require_project_admin`.
  - `get_settings` — singleton config.
  - `get_logger` — structlog logger bound to `request_id` + `user_id`.

### 11.4 Transaction Handling

```python
# app/api/dependencies/db.py
async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- One transaction per HTTP request by default.
- Services explicitly call `await session.flush()` when they need IDs mid-transaction (e.g., FK to a just-created row).
- Activity log writes are part of the same transaction — atomicity guaranteed.

### 11.5 Task Assignment Validation

```python
async def assign_task(task: Task, new_assignee_id: UUID, db: AsyncSession) -> None:
    is_member = await project_members_repo.exists(
        db, project_id=task.project_id, user_id=new_assignee_id
    )
    if not is_member:
        raise BusinessError("ASSIGNEE_NOT_MEMBER")
    task.assignee_id = new_assignee_id
```

### 11.6 Status FSM

```python
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO:        {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.IN_REVIEW, TaskStatus.TODO},
    TaskStatus.IN_REVIEW:   {TaskStatus.DONE, TaskStatus.IN_PROGRESS},
    TaskStatus.DONE:        {TaskStatus.IN_REVIEW},  # reopen
}

def transition(task: Task, new: TaskStatus) -> None:
    if new not in ALLOWED_TRANSITIONS[task.status]:
        raise BusinessError("INVALID_TASK_TRANSITION",
                            details={"from": task.status, "to": new,
                                     "allowed": list(ALLOWED_TRANSITIONS[task.status])})
    task.status = new
    task.completed_at = datetime.now(tz=UTC) if new == TaskStatus.DONE else None
```

### 11.7 Overdue Calculation

A task is **overdue** iff:
- `due_date IS NOT NULL`
- `due_date < CURRENT_DATE` (DB server's date)
- `status <> 'done'`
- `deleted_at IS NULL`

Computed in SQL for dashboard counts (not in Python).

### 11.8 Activity Logging

```python
async def log_activity(db: AsyncSession, *, actor_id, project_id, entity_type,
                       entity_id, action, metadata):
    db.add(ActivityLog(
        actor_id=actor_id, project_id=project_id,
        entity_type=entity_type, entity_id=entity_id,
        action=action, metadata=metadata,
    ))
```

Called by services after every mutation, **before** the request-level commit, so it joins the same transaction.

### 11.9 Invitation Workflow (MVP)

1. Admin posts `{email, role}`.
2. `member_service` normalizes email → looks up user.
3. If not found → `404 USER_NOT_FOUND`. (Email invite flow is post-MVP.)
4. Insert `project_members` row.
5. Log `MEMBER_INVITED`.

---

## 12. FastAPI Backend Architecture

### 12.1 Routers

- One router file per resource: `routes/auth.py`, `routes/projects.py`, `routes/members.py`, `routes/tasks.py`, `routes/dashboard.py`, `routes/health.py`.
- Each router declares its `prefix` and `tags`.
- Aggregated by `app/api/__init__.py` → `api_router` → mounted on `app` with `/v1` prefix.

### 12.2 Middleware

Order matters. Applied bottom-up (innermost last on the way in):

1. `RequestIDMiddleware` — issues `request_id`; sets in `contextvars` for structlog.
2. `LoggingMiddleware` — logs request start/end with status, latency, user, route.
3. `CORSMiddleware` — strict allow-list from env.
4. `GZipMiddleware` — for responses ≥ 1 KB.
5. `RateLimitMiddleware` — token-bucket per IP + per user; backed by Redis if available, else in-memory.
6. `ExceptionToProblemMiddleware` — converts uncaught exceptions to the standard error envelope.

### 12.3 Exception Handlers

```python
@app.exception_handler(BusinessError)
async def business_handler(request: Request, exc: BusinessError) -> JSONResponse: ...

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc) -> JSONResponse: ...

@app.exception_handler(Exception)
async def fallback_handler(request, exc) -> JSONResponse:
    logger.exception("unhandled_error", exc_info=exc)
    return JSONResponse(status_code=500, content={...})
```

### 12.4 Schema Layer

- `schemas/` mirrors `models/` but defines **Pydantic v2** request/response shapes.
- Each resource has `Create`, `Update`, `Read`, optionally `Public` variants.
- Response models declared on every endpoint via `response_model=` to clip leaks and produce strict OpenAPI.

### 12.5 OpenAPI Documentation

- Swagger UI at `/docs` (dev/staging only — guarded by env).
- ReDoc at `/redoc`.
- All endpoints carry `summary`, `description`, response examples, and explicit `responses=` for error codes.
- `openapi.json` committed to `apps/api/openapi.json` via CI on `main` for downstream code generators.

### 12.6 Backend Folder Tree

```txt
apps/
└── api/
    ├── app/
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── dependencies/
    │   │   │   ├── __init__.py
    │   │   │   ├── auth.py            # get_current_user, oauth2_scheme
    │   │   │   ├── db.py              # get_db session yield
    │   │   │   ├── rbac.py            # require_project_member, require_project_admin
    │   │   │   └── pagination.py      # PaginationParams
    │   │   └── routes/
    │   │       ├── __init__.py
    │   │       ├── auth.py
    │   │       ├── projects.py
    │   │       ├── members.py
    │   │       ├── tasks.py
    │   │       ├── dashboard.py
    │   │       └── health.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py              # pydantic-settings Settings
    │   │   ├── logging.py             # structlog config
    │   │   ├── security.py            # bcrypt, JWT encode/decode
    │   │   ├── exceptions.py          # BusinessError, ErrorCode enum
    │   │   └── time.py                # utc_now() helper
    │   ├── db/
    │   │   ├── __init__.py
    │   │   ├── base.py                # DeclarativeBase
    │   │   ├── session.py             # AsyncEngine, AsyncSessionLocal
    │   │   └── types.py               # GUID, TimestampMixin
    │   ├── middleware/
    │   │   ├── __init__.py
    │   │   ├── request_id.py
    │   │   ├── logging.py
    │   │   ├── rate_limit.py
    │   │   └── exceptions.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── user.py
    │   │   ├── project.py
    │   │   ├── project_member.py
    │   │   ├── task.py
    │   │   ├── refresh_token.py
    │   │   └── activity_log.py
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── user.py
    │   │   ├── project.py
    │   │   ├── member.py
    │   │   ├── task.py
    │   │   ├── dashboard.py
    │   │   └── common.py              # Envelope, ErrorPayload, Pagination
    │   ├── repositories/
    │   │   ├── __init__.py
    │   │   ├── base.py                # BaseRepo[T]
    │   │   ├── users.py
    │   │   ├── projects.py
    │   │   ├── project_members.py
    │   │   ├── tasks.py
    │   │   ├── refresh_tokens.py
    │   │   └── activity_logs.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── projects.py
    │   │   ├── members.py
    │   │   ├── tasks.py
    │   │   ├── dashboard.py
    │   │   └── activity.py
    │   ├── utils/
    │   │   ├── __init__.py
    │   │   ├── ids.py
    │   │   ├── slug.py
    │   │   └── pagination.py
    │   └── main.py                    # FastAPI app factory
    ├── tests/
    │   ├── conftest.py
    │   ├── factories.py
    │   ├── unit/
    │   ├── integration/
    │   └── e2e/
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    ├── alembic.ini
    ├── pyproject.toml
    ├── uv.lock
    ├── .env.example
    ├── Dockerfile
    └── README.md
```

---

## 13. Frontend Architecture

### 13.1 Principles

- **Feature-based** organization, not type-based. Each feature owns its components, hooks, and API calls.
- **Server state** in TanStack Query, **client state** in Zustand (auth, UI flags). No duplication.
- **One API client** (`src/lib/api/client.ts`); domain functions wrap it.
- **One form pattern**: React Hook Form + Zod resolver, shared `<FormField>` primitive.
- **Route-level code splitting** via `React.lazy()`.

### 13.2 Folder Structure

```txt
apps/
└── web/
    ├── public/
    │   └── favicon.svg
    ├── src/
    │   ├── app/
    │   │   ├── App.tsx
    │   │   ├── router.tsx
    │   │   ├── providers.tsx          # QueryClient, ZustandHydration, Theme
    │   │   └── error-boundary.tsx
    │   ├── components/
    │   │   ├── ui/                    # Button, Input, Card, Dialog, Toast, Skeleton
    │   │   ├── layout/                # AppShell, Sidebar, Topbar
    │   │   └── feedback/              # EmptyState, ErrorState, LoadingState
    │   ├── features/
    │   │   ├── auth/
    │   │   │   ├── api.ts             # login, signup, refresh, logout, me
    │   │   │   ├── hooks.ts           # useLogin, useSignup, useMe
    │   │   │   ├── schemas.ts         # Zod schemas
    │   │   │   ├── pages/             # LoginPage, SignupPage
    │   │   │   └── components/
    │   │   ├── projects/
    │   │   │   ├── api.ts
    │   │   │   ├── hooks.ts
    │   │   │   ├── schemas.ts
    │   │   │   ├── pages/             # ProjectsListPage, ProjectDetailPage
    │   │   │   └── components/        # ProjectCard, ProjectForm, MemberList
    │   │   ├── tasks/
    │   │   │   ├── api.ts
    │   │   │   ├── hooks.ts
    │   │   │   ├── schemas.ts
    │   │   │   ├── pages/
    │   │   │   └── components/        # TaskCard, TaskForm, StatusBadge, KanbanColumn
    │   │   └── dashboard/
    │   │       ├── api.ts
    │   │       ├── hooks.ts
    │   │       ├── pages/             # DashboardPage
    │   │       └── components/        # StatCard, RecentActivityFeed
    │   ├── hooks/
    │   │   ├── useDebounce.ts
    │   │   ├── useMediaQuery.ts
    │   │   └── useKeyboardShortcut.ts
    │   ├── lib/
    │   │   ├── api/
    │   │   │   ├── client.ts          # Axios instance + interceptors
    │   │   │   ├── errors.ts          # parseApiError
    │   │   │   └── types.ts           # Envelope<T>, ApiError
    │   │   ├── auth/
    │   │   │   └── token.ts           # in-memory access token holder
    │   │   ├── query/
    │   │   │   └── client.ts          # queryClient defaults
    │   │   └── utils/
    │   │       ├── cn.ts              # classnames helper
    │   │       └── format.ts          # date, status, priority formatters
    │   ├── store/
    │   │   ├── auth.ts                # Zustand auth slice
    │   │   └── ui.ts                  # sidebar collapsed, theme, etc.
    │   ├── routes/
    │   │   ├── ProtectedRoute.tsx
    │   │   └── RequireProjectAdmin.tsx
    │   ├── styles/
    │   │   ├── index.css              # @tailwind base/components/utilities
    │   │   └── tokens.ts              # spacing/colors as TS constants
    │   ├── types/
    │   │   ├── api.ts                 # shared API DTO types
    │   │   └── env.d.ts
    │   ├── tests/
    │   │   ├── setup.ts
    │   │   └── utils.tsx              # renderWithProviders
    │   ├── main.tsx
    │   └── vite-env.d.ts
    ├── e2e/
    │   ├── auth.spec.ts
    │   ├── projects.spec.ts
    │   └── tasks.spec.ts
    ├── index.html
    ├── package.json
    ├── pnpm-lock.yaml
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── postcss.config.js
    ├── eslint.config.js
    ├── playwright.config.ts
    └── .env.example
```

### 13.3 State Management

| State | Tool | Reason |
|---|---|---|
| Server data (projects, tasks, etc.) | TanStack Query | Cache, dedupe, mutation invalidation |
| Auth (access token, user) | Zustand | Tiny, synchronous, persistent across components |
| Ephemeral UI (modals, sidebar) | Zustand | Co-located with auth |
| Form state | React Hook Form | Uncontrolled, performant |
| URL state (filters, pagination) | React Router search params | Shareable links |

### 13.4 API Client

```ts
// src/lib/api/client.ts
import axios from "axios";
import { getAccessToken, setAccessToken, clearAuth } from "@/lib/auth/token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true,
  timeout: 15_000,
});

api.interceptors.request.use((c) => {
  const t = getAccessToken();
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});

let refreshing: Promise<string> | null = null;
api.interceptors.response.use(undefined, async (err) => {
  if (err.response?.status === 401 && !err.config._retry) {
    err.config._retry = true;
    refreshing ??= refreshAccessToken().finally(() => (refreshing = null));
    const newToken = await refreshing.catch(() => null);
    if (!newToken) { clearAuth(); throw err; }
    err.config.headers.Authorization = `Bearer ${newToken}`;
    return api(err.config);
  }
  throw err;
});
```

### 13.5 Protected Routes

```tsx
// src/routes/ProtectedRoute.tsx
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useMe();
  const location = useLocation();
  if (isLoading) return <FullPageSkeleton />;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  return <>{children}</>;
}
```

### 13.6 Error Boundary

Top-level `<ErrorBoundary>` catches render-time errors, logs to monitoring, shows a "Something went wrong — refresh" screen with a request-id for support.

### 13.7 Lazy Loading

```tsx
const ProjectsPage = lazy(() => import("@/features/projects/pages/ProjectsListPage"));
```

Wrapped in `<Suspense fallback={<RouteSkeleton />}>` at the router boundary.

---

## 14. UI/UX Guidelines

### 14.1 Design System

- **Component primitives** in `components/ui/` built atop Radix UI primitives + Tailwind variants.
- Headless logic + accessible defaults from Radix; styling owned by us.

### 14.2 Typography

| Token | Use |
|---|---|
| `text-xs` (12 px) | Captions, meta |
| `text-sm` (14 px) | Body |
| `text-base` (16 px) | Form inputs |
| `text-lg` (18 px) | Section headers |
| `text-2xl` (24 px) | Page titles |
| `font-medium` | Default emphasis |
| `font-semibold` | Headings |

System font stack: Inter → SF Pro → Segoe UI → Roboto → sans-serif.

### 14.3 Spacing

Tailwind's 4-px scale, used in multiples of 4. Layout grids use `gap-4` / `gap-6` / `gap-8`. No magic px values.

### 14.4 Colors

| Token | Value (light) | Use |
|---|---|---|
| `bg` | `#FFFFFF` | App background |
| `surface` | `#F8FAFC` | Cards |
| `border` | `#E2E8F0` | Dividers |
| `text` | `#0F172A` | Body |
| `text-muted` | `#64748B` | Secondary |
| `primary` | `#4F46E5` | CTAs |
| `success` | `#16A34A` | Done states |
| `warning` | `#D97706` | Overdue, in-review |
| `danger` | `#DC2626` | Destructive |
| `info` | `#0284C7` | Notices |

Dark theme mirrors with WCAG-AA contrast.

### 14.5 Layout Principles

- App shell: **left sidebar** (projects), **top bar** (search, user menu), **main content**.
- Max content width 1280 px; centered.
- Forms: single-column, label above input, 8-px gap.

### 14.6 Accessibility

- Color contrast ≥ 4.5:1 for body text.
- All interactive elements keyboard-reachable; focus rings visible.
- ARIA attributes provided by Radix; never hand-roll.
- `prefers-reduced-motion` respected.
- Form errors associated with `aria-describedby`.

### 14.7 State Patterns

| State | Pattern |
|---|---|
| Loading | Skeleton matching final layout; never bare spinner > 300 ms |
| Empty | Illustration + headline + primary CTA |
| Error | Friendly message + request-id + retry button |
| Disabled | `aria-disabled` + reduced opacity + cursor `not-allowed` |
| Success | Toast top-right, auto-dismiss 4 s |

### 14.8 Responsive Behavior

- Mobile-first; breakpoints `sm:640 md:768 lg:1024 xl:1280`.
- Sidebar collapses into a drawer below `md`.
- Tables → cards below `md`.
- Touch targets ≥ 44 × 44.

---

## 15. Validation Rules

### 15.1 Centralized Rules

| Field | Rule |
|---|---|
| Email | RFC 5322, max 254, lowercase |
| Password | 12–128, ≥ 1 letter, ≥ 1 digit, not common-password (zxcvbn ≥ 3 in production) |
| Name | 1–80, trimmed |
| Project name | 2–80, unique per owner |
| Project description | ≤ 2,000 |
| Task title | 2–140 |
| Task description | ≤ 10,000 |
| Due date | ≥ today, ≤ today + 5 years |
| Priority | `low | medium | high | critical` |
| Status | `todo | in_progress | in_review | done` |
| UUID params | strict v4 |

### 15.2 Pydantic v2 Example

```python
# app/schemas/task.py
from datetime import date
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.models.task import TaskPriority, TaskStatus

class TaskCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=10_000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: date | None = None

    @field_validator("due_date")
    @classmethod
    def not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("due_date must be today or later")
        return v
```

### 15.3 Zod Mirror

```ts
// src/features/tasks/schemas.ts
import { z } from "zod";

export const TaskCreateSchema = z.object({
  title: z.string().trim().min(2).max(140),
  description: z.string().max(10_000).optional().default(""),
  priority: z.enum(["low", "medium", "high", "critical"]).default("medium"),
  assignee_id: z.string().uuid().nullable().optional(),
  due_date: z.string().date().nullable().optional()
    .refine((v) => !v || v >= new Date().toISOString().slice(0, 10),
            "Due date cannot be in the past"),
});
export type TaskCreate = z.infer<typeof TaskCreateSchema>;
```

### 15.4 Duplicate Prevention

- DB unique constraints are the source of truth.
- Repositories catch `IntegrityError` → service raises typed `BusinessError`.
- UI surfaces the field-level error from the response envelope.

---

## 16. Error Handling Standards

### 16.1 Standard Error Envelope

```json
{
  "success": false,
  "error": {
    "code": "INVALID_TASK_TRANSITION",
    "message": "Cannot move task from 'done' to 'todo'",
    "details": {
      "from": "done",
      "to": "todo",
      "allowed": ["in_review"]
    }
  },
  "meta": {
    "request_id": "req_01JCK2X8QY..."
  }
}
```

Validation errors include `details.fields`:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Request body validation failed",
    "details": {
      "fields": {
        "title": ["String should have at least 2 characters"],
        "due_date": ["due_date must be today or later"]
      }
    }
  },
  "meta": { "request_id": "..." }
}
```

### 16.2 HTTP Status Standards

See [10.4](#104-status-code-standards).

### 16.3 Global Exception Handlers

- `BusinessError` → mapped status from `ErrorCode → HTTP` table.
- `RequestValidationError` → `422` with field map.
- `IntegrityError` → mapped to `409 *_TAKEN` per constraint name.
- `HTTPException` → passthrough.
- Anything else → `500 INTERNAL_ERROR` + Sentry capture.

### 16.4 Retry Strategy

- **Backend → DB**: no retries; surface 5xx.
- **Backend → external (future)**: tenacity with exponential backoff, jitter, max 3 attempts.
- **Frontend → API (GET)**: TanStack Query default — 3 retries with exponential backoff.
- **Frontend → API (mutation)**: never auto-retry; ask user.

### 16.5 Frontend Toast Handling

- Success: top-right, 4 s, dismissible.
- Error: top-right, sticky until dismissed, includes request-id for support, "Retry" button on idempotent ops.

### 16.6 Request Correlation

- Generated server-side if missing; echoed in `X-Request-Id` response header.
- Logged on both ends; shown to user in error UI.

---

## 17. Security Best Practices

### 17.1 OWASP Top-10 Mitigation Matrix

| OWASP | Mitigation |
|---|---|
| A01 Broken Access Control | Server-side RBAC dependencies on every endpoint; 404 vs 403 to avoid enumeration |
| A02 Cryptographic Failures | TLS at edge; bcrypt cost 12; JWT secrets from env; no MD5/SHA1 |
| A03 Injection | SQLAlchemy parameterized queries only; Pydantic strict input parsing |
| A04 Insecure Design | This document; threat-model checklist (Section 32) |
| A05 Security Misconfiguration | Strict CORS allow-list; HSTS; `/docs` disabled in prod |
| A06 Vulnerable Components | Weekly `pip-audit`, `pnpm audit`, Dependabot |
| A07 Authentication Failures | Rate-limited login; lockout; refresh rotation + reuse detection |
| A08 Software & Data Integrity | Signed commits encouraged; locked lockfiles; CI provenance |
| A09 Logging & Monitoring | Structured JSON logs; correlation IDs; no PII in logs |
| A10 SSRF | No URL fetching in MVP; allow-list when added |

### 17.2 JWT Handling

- Algorithm: HS256 in MVP (single service); RS256 if/when introducing multiple services or third-party verifiers.
- Access token TTL: **15 min**; refresh TTL: **14 days**.
- Claims: `sub`, `iat`, `exp`, `jti`, `type` (`access` | `refresh`).
- Access token stored **in memory** (Zustand) — never `localStorage`.

### 17.3 Refresh Token Rotation

- One refresh token per family at a time.
- On use → mark `used_at`, issue new with same `family_id`.
- On reuse of a `used_at != NULL` token → revoke entire family.

### 17.4 Cookies

- `refresh_token` cookie: `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/v1/auth`, `Max-Age=14d`.

### 17.5 CORS

```python
allow_origins=settings.FRONTEND_URLS  # explicit list, no "*"
allow_credentials=True
allow_methods=["GET","POST","PATCH","PUT","DELETE","OPTIONS"]
allow_headers=["Authorization","Content-Type","If-Match","Idempotency-Key","X-Request-Id"]
expose_headers=["X-Request-Id"]
```

### 17.6 Rate Limiting

- Unauthenticated `/auth/*`: 10 req / 5 min / IP.
- Authenticated endpoints: 120 req / min / user.
- 429 includes `Retry-After`.

### 17.7 Password Hashing

```python
from passlib.context import CryptContext
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
```

### 17.8 Input Sanitization

- All HTML rendered through React (auto-escaped).
- No `dangerouslySetInnerHTML` in the codebase (enforced via ESLint).
- Description fields plaintext on backend; if/when rich text added, sanitize server-side with `bleach`.

### 17.9 Secrets Management

- All secrets via environment variables.
- `.env` files git-ignored.
- Railway variables encrypted at rest.
- Rotating keys documented in `docs/runbooks/secret-rotation.md`.

---

## 18. Performance Optimization

### 18.1 Backend

- **Connection pool**: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`.
- **N+1 prevention**: `selectinload`/`joinedload` for known relations; lints in code review.
- **Pagination**: cap `size` at 100; default 20.
- **Composite indexes** sized to query plans (see [9.3](#93-indexing-strategy)).
- **Bulk operations**: use `bulk_insert_mappings` for ActivityLog batches.
- **gzip** for responses ≥ 1 KB.
- **HTTP cache** headers on static GETs (`/auth/me` has `Cache-Control: no-store`).

### 18.2 Frontend

- **Code splitting** at route boundaries.
- **React.memo** on heavy list rows; `useMemo` for derived state ≥ O(n).
- **Debounce** search inputs at 250 ms.
- **TanStack Query** staleTime: 30 s on lists, 5 m on profile.
- **Image** optimization: SVG icons; raster assets served as WebP.
- **Tree-shaking**: avoid barrel imports for large libs (`date-fns` named imports).
- **Bundle analysis**: `vite-plugin-visualizer` in CI; PR comment on regressions ≥ 5%.

### 18.3 Caching

- Optional Redis layer for `/dashboard/stats` (TTL 60 s) and `/auth/me` (TTL 30 s).
- Cache invalidation on relevant mutations via `cache.invalidate_tags(...)`.

---

## 19. Testing Strategy

### 19.1 Pyramid

```
                E2E (Playwright)
            ───────────────────────
          Integration (httpx + pg)
       ─────────────────────────────
      Unit (pytest, vitest)
   ───────────────────────────────────
```

### 19.2 Backend Tests

- **Framework**: pytest + pytest-asyncio + httpx AsyncClient.
- **DB**: dedicated PostgreSQL test database; fresh migrations per session; per-test rollback via outer transaction.
- **Factories**: factory-boy for User/Project/Task.
- **Unit**: services tested with in-memory fakes for repositories.
- **Integration**: real DB; full request flow through ASGI without a network socket.
- **Coverage gate**: ≥ 80% lines (`pytest --cov=app --cov-fail-under=80`).

```python
# tests/conftest.py
@pytest_asyncio.fixture
async def client(db_session) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### 19.3 Frontend Tests

- **Unit/component**: Vitest + React Testing Library.
- **MSW** for HTTP mocking at the network boundary.
- **E2E**: Playwright against staging or local docker-compose; covers golden paths: signup → create project → invite → create task → mark done.
- **Coverage gate**: ≥ 70% statements.

### 19.4 CI

- Unit + integration on every PR; E2E on `main` + nightly.
- Failures block merge.

---

## 20. Logging & Monitoring

### 20.1 Structured Logging (Backend)

- `structlog` with JSON renderer in production, pretty renderer in dev.
- Every log line includes `request_id`, `user_id` (if authenticated), `route`, `latency_ms`, `status`.
- Log levels: `DEBUG` (dev), `INFO` (request lifecycle), `WARNING` (degraded), `ERROR` (handled exceptions), `CRITICAL` (uncaught).

### 20.2 Frontend Logging

- `console.error` reserved for unexpected; piped to Sentry.
- User-visible errors include request-id from the API response.

### 20.3 Health Check

```python
@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "db": "ok",
        "version": settings.APP_VERSION,
        "commit": settings.GIT_SHA,
        "time": datetime.now(tz=UTC).isoformat(),
    }
```

Railway health-check path: `/health`. Timeout 5 s. 3 failures → restart.

### 20.4 Monitoring

- Railway built-in metrics for CPU/memory/network.
- Sentry for error tracking (backend + frontend).
- (Future) Prometheus exporter + Grafana for fine-grained metrics.

### 20.5 Correlation IDs

- `X-Request-Id` header generated by middleware if absent; propagated to logs and error responses; surfaced in UI toasts.

---

## 21. Deployment Guide (Railway)

### 21.1 Services

| Service | Build | Start | Health |
|---|---|---|---|
| `api` | `uv sync --no-dev && alembic upgrade head` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2` | `/health` |
| `web` | `pnpm install --frozen-lockfile && pnpm build` | `pnpm preview --port $PORT --host` (or a static serve adapter) | `/` |
| `postgres` | managed addon | — | provider |
| `redis` (optional) | managed addon | — | provider |

### 21.2 railway.toml (api)

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 21.3 Production Migrations

- Migrations run on **deploy**, not at app start.
- Migration job exits non-zero → deploy halts → previous version stays live.
- Backward-compatible migration pattern enforced (expand → migrate code → contract).

### 21.4 Railway CLI

```bash
railway login
railway link
railway variables set JWT_SECRET=...
railway up
railway logs --service api
railway run uv run alembic upgrade head
```

### 21.5 Rollback

- `railway redeploy --service api --deployment <previous>` for image rollback.
- For destructive migrations: explicit `downgrade -1` revision must exist before merge; otherwise expand/contract.

### 21.6 Deployment Checklist

- [ ] All env vars set in Railway (Section 22).
- [ ] `DATABASE_URL` provided by Railway PG addon.
- [ ] `JWT_SECRET`, `JWT_REFRESH_SECRET` set to 32+ random bytes (base64).
- [ ] `FRONTEND_URL` and CORS allow-list match deployed web URL.
- [ ] `ENVIRONMENT=production`.
- [ ] `/docs` disabled in prod env.
- [ ] Sentry DSN set on both services.
- [ ] Health check responds < 5 s.
- [ ] First request to `/auth/me` returns 401 (sanity).
- [ ] Smoke test: signup → create project → create task.

### 21.7 Production Readiness Checklist

- [ ] HTTPS enforced (Railway default).
- [ ] HSTS header set.
- [ ] Rate limits enabled.
- [ ] Backups verified (point-in-time recovery checked monthly).
- [ ] Alembic migrations idempotent.
- [ ] Sentry capture verified.
- [ ] Lighthouse Performance ≥ 90, Accessibility ≥ 95.
- [ ] axe-core pass (no critical).

---

## 22. Environment Variables

### 22.1 Backend

| Var | Type | Example | Description |
|---|---|---|---|
| `ENVIRONMENT` | enum | `production` | `local`, `test`, `staging`, `production` |
| `APP_VERSION` | str | `1.0.0` | Surfaced in `/health` and logs |
| `GIT_SHA` | str | `abc1234` | Set by build; logged & on `/health` |
| `DATABASE_URL` | url | `postgresql+asyncpg://user:pass@host:5432/db` | Async driver required |
| `DATABASE_POOL_SIZE` | int | `10` | SQLAlchemy pool |
| `DATABASE_MAX_OVERFLOW` | int | `20` | |
| `REDIS_URL` | url | `redis://...` | Optional |
| `JWT_SECRET` | str | random 32+ bytes b64 | Access-token signing |
| `JWT_REFRESH_SECRET` | str | random 32+ bytes b64 | Refresh-token signing |
| `JWT_ACCESS_TTL_SECONDS` | int | `900` | 15 min |
| `JWT_REFRESH_TTL_SECONDS` | int | `1209600` | 14 days |
| `BCRYPT_ROUNDS` | int | `12` | |
| `FRONTEND_URLS` | csv | `https://app.example.com` | CORS allow-list |
| `RATE_LIMIT_AUTH_PER_5MIN` | int | `10` | |
| `RATE_LIMIT_USER_PER_MIN` | int | `120` | |
| `SENTRY_DSN` | str | `https://...` | Optional |
| `LOG_LEVEL` | enum | `INFO` | |
| `DOCS_ENABLED` | bool | `false` | Disable `/docs` in prod |

### 22.2 Frontend

| Var | Example | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `https://api.example.com/v1` | API base |
| `VITE_SENTRY_DSN` | `https://...` | Optional |
| `VITE_ENVIRONMENT` | `production` | |
| `VITE_COMMIT_SHA` | `abc1234` | Surfaced in footer / error UI |

### 22.3 `.env.example` (backend excerpt)

```env
ENVIRONMENT=local
APP_VERSION=0.1.0
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ttm
JWT_SECRET=replace-me-32-bytes-base64
JWT_REFRESH_SECRET=replace-me-32-bytes-base64
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=1209600
FRONTEND_URLS=http://localhost:5173
LOG_LEVEL=DEBUG
DOCS_ENABLED=true
```

---

## 23. Git Workflow

### 23.1 Branching

- `main` — always deployable.
- `feature/<short-kebab>` — new functionality.
- `fix/<short-kebab>` — bug fixes.
- `chore/<short-kebab>` — tooling, deps, docs.
- `refactor/<short-kebab>` — non-functional changes.
- No long-lived branches.

### 23.2 Conventional Commits

```
<type>(<scope>): <subject>

[optional body]

[optional footer: BREAKING CHANGE, Refs #123]
```

Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`, `build`, `ci`.

Examples:
```bash
feat(auth): implement JWT login flow
fix(tasks): validate assignee is project member
refactor(repositories): extract BaseRepo[T]
chore(deps): bump fastapi to 0.115.0
test(projects): add membership boundary cases
```

### 23.3 Pull Requests

- Title follows conventional-commit format.
- Description: **Why**, **What**, **How to test**, **Screenshots** (UI), linked issue.
- ≤ 400 changed lines preferred; split otherwise.
- Required: green CI, 1 review, no unresolved comments.

### 23.4 Merge Strategy

- **Squash merge** to `main` with the conventional-commit title becoming the squash message.
- No rebase merges (history clarity).
- No merge commits.

### 23.5 Commit Hygiene

- Pre-commit hooks: ruff, black, mypy (lite), eslint, prettier, secret-scan.
- WIP commits squashed before opening PR.
- No `console.log`, no `print`, no `TODO` without an issue link.

---

## 24. Code Style & Engineering Rules

### 24.1 Frontend

- **TypeScript strict mode** — `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`.
- **No `any`** — `eslint-no-explicit-any: error`. Use `unknown` + narrowing.
- **No default exports** for components — named exports only (refactor-friendly).
- **Folder per feature**, not per type.
- **Hooks** prefixed `use*`; one hook per file when ≥ 30 LOC.
- **Components** PascalCase; files match component name.
- **Imports** sorted: external → `@/` aliases → relative; enforced by ESLint.
- **No barrel files** at feature root (kills tree-shaking and IDE jump-to).
- **ESLint + Prettier** configs versioned; CI fails on lint errors.

### 24.2 Backend

- **Type hints mandatory** on every function and method, including `__init__`.
- **mypy --strict** in CI; no `# type: ignore` without a comment.
- **ruff** rules: `E,F,I,B,UP,N,SIM,RUF,ASYNC`.
- **black** with default 88-col line length.
- **No raw SQL** in routes; only in repositories (`text()` allowed when justified).
- **No business logic** in routes or repositories — services only.
- **No `print`** — `structlog` only.
- **No `from x import *`**.
- **Dependency injection** for all cross-cutting concerns; no module-level singletons in services.
- **Naming**: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants, modules `snake_case`.

### 24.3 API Conventions

- Plural resource nouns: `/projects`, `/tasks`.
- Nested for ownership: `/projects/{id}/tasks`.
- Verbs only for non-CRUD: `/projects/{id}/transfer-owner`.
- Status changes via dedicated subresource: `PATCH /tasks/{id}/status`.

---

## 25. Commands Cheat Sheet

### 25.1 Backend (uv)

```bash
# Bootstrap
cd apps/api
uv venv
source .venv/bin/activate
uv sync

# Run
uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "create users"
alembic upgrade head
alembic downgrade -1
alembic history

# Quality
ruff check . --fix
black .
mypy .
pytest -q
pytest --cov=app --cov-report=term-missing
```

### 25.2 Frontend (pnpm)

```bash
cd apps/web
pnpm install
pnpm dev                # vite dev server
pnpm build              # production build
pnpm preview            # serve built output
pnpm lint               # eslint
pnpm typecheck          # tsc --noEmit
pnpm test               # vitest
pnpm test:e2e           # playwright
```

### 25.3 Database (local docker-compose)

```bash
docker compose up -d postgres
psql $DATABASE_URL
```

### 25.4 Railway

```bash
railway login
railway link
railway up
railway logs --service api --tail
railway run uv run alembic upgrade head
```

### 25.5 Make (root)

```bash
make bootstrap          # install everything
make dev                # run api + web concurrently
make test               # all tests
make fmt                # format both ends
make lint               # lint both ends
make migrate            # alembic upgrade head
make migration name=…   # generate new migration
```

---

## 26. Edge Cases & Critical Rules

| # | Edge case | Strategy |
|---|---|---|
| 1 | **Duplicate invitations** | Unique constraint on `(project_id, user_id)`; service returns `409 ALREADY_MEMBER` |
| 2 | **Expired JWT** | Axios 401 interceptor calls `/auth/refresh` once; if refresh fails → redirect login |
| 3 | **Reused refresh token** | Revoke entire family; force re-login; security log entry |
| 4 | **Concurrent task edits** | `If-Match: <updated_at>` header; mismatch → `412 PRECONDITION_FAILED`; UI prompts merge |
| 5 | **Unauthorized access to project** | Return `404 PROJECT_NOT_FOUND` (no enumeration) |
| 6 | **Role escalation attempt** | RBAC dependency rejects with `403`; logged |
| 7 | **Network failures (frontend)** | TanStack Query retry x3 on GET; mutations surface error toast with Retry |
| 8 | **Lost DB connection** | `pool_pre_ping=True` + 5xx returned; client retries idempotent GETs |
| 9 | **Invalid task transition** | FSM check returns `422` with `allowed` list |
| 10 | **Task assigned to removed member** | FK `ON DELETE SET NULL` + removal service nulls assignee; UI shows "Unassigned" |
| 11 | **Empty dashboard** | Empty-state copy + CTA "Create your first project" |
| 12 | **Partial failure mid-transaction** | One transaction per request; full rollback; activity log included |
| 13 | **Failed migration on deploy** | Migration step exits non-zero; deploy halts; previous version remains live |
| 14 | **Last admin demotion** | Service checks count; rejects with `409 LAST_ADMIN` |
| 15 | **Self-removal of owner** | Rejected `409 CANNOT_REMOVE_OWNER`; user must transfer first |
| 16 | **Soft-deleted user lookup in invites** | Query filters `deleted_at IS NULL`; returns `404 USER_NOT_FOUND` |
| 17 | **Timezone confusion** | All times UTC at DB and API; UI converts on display |
| 18 | **DST-affected due dates** | `due_date` stored as `DATE` (no time component) — no DST issues |
| 19 | **Race in refresh rotation** | DB transaction + unique constraint on active jti per family |
| 20 | **Long-running task list query** | Server-side pagination; hard cap `size=100` |
| 21 | **Browser back after logout** | Sensitive pages re-check `/auth/me`; render-gate on user presence |
| 22 | **API version mismatch** | `/v1` prefix; new major version goes to `/v2`; old never deleted within deprecation window |
| 23 | **Cookie blocked (Safari 3rd-party)** | Hosted on first-party domain; `SameSite=Strict` requires same-site setup |
| 24 | **Rate-limit lockout for legit user** | Per-user not per-IP for authenticated; documented `Retry-After` |

---

## 27. Acceptance Criteria

### Authentication
- User can sign up, log in, view profile, log out.
- Wrong password is indistinguishable from unknown email.
- Access token expires in 15 min; refresh auto-renews seamlessly.
- 10 failed login attempts → lockout for 15 min.

### Projects
- Authenticated user creates project; appears in list immediately.
- Non-member cannot read project (returns `404`).
- Admin can edit/soft-delete; Member cannot.
- Soft-deleted project disappears from lists.

### Tasks
- Member creates a task; assigning to a non-member fails with `422`.
- Status transitions enforce FSM.
- Filtering, sorting, pagination work on list endpoints.

### Dashboard
- Counts match the underlying tasks visible to the user.
- Overdue equals: not done AND `due_date < today`.
- Empty state shown when there are zero projects.

### Deployment
- Single push to `main` triggers Railway deploy.
- Migrations run before app start; failed migration halts deploy.
- `/health` returns 200 within 5 s.

### Security
- All authenticated endpoints reject missing/expired tokens.
- Refresh-token reuse triggers family revocation.
- CORS allow-list rejects unknown origins.

### Mobile Responsiveness
- Layout usable on 360 px without horizontal scroll.
- Touch targets ≥ 44 × 44.

### Error Handling
- All errors conform to envelope shape.
- All errors include `request_id`.

### Logging
- Every request emits one structured line with `request_id`, `user_id`, `status`, `latency_ms`.
- No PII in logs (verified by grep on synthetic test).

### Validation
- Both ends enforce identical rules; backend never trusts frontend.

---

## 28. README Structure

```markdown
# Team Task Manager

> Production-grade full-stack task management with project-scoped RBAC.

## Demo
[Live](https://...) · Demo user: `demo@example.com` / `DemoPass123!`

## Stack
FastAPI · SQLAlchemy 2.0 · PostgreSQL · React · Vite · TypeScript · TailwindCSS · TanStack Query

## Architecture
See [SPECIFICATION.md](./SPECIFICATION.md) §8.

## Screenshots
| Dashboard | Project | Task |
|-|-|-|
| ![](docs/img/dashboard.png) | ![](docs/img/project.png) | ![](docs/img/task.png) |

## Local Setup
1. `git clone … && cd team-task-manager`
2. `cp apps/api/.env.example apps/api/.env`
3. `cp apps/web/.env.example apps/web/.env`
4. `docker compose up -d postgres`
5. `make bootstrap`
6. `make migrate`
7. `make dev` → http://localhost:5173

## Environment Variables
See SPECIFICATION.md §22.

## API
OpenAPI: http://localhost:8000/docs · Spec: [openapi.json](./apps/api/openapi.json)

## Testing
`make test` — runs backend + frontend + e2e.

## Deployment
Railway: see SPECIFICATION.md §21.

## Contributing
See `CONTRIBUTING.md` — branch naming, conventional commits, PR template.

## License
MIT
```

---

## 29. Development Phases

### Phase 1 — Repository Setup
- **Deliverables**: monorepo (`apps/api`, `apps/web`), root `Makefile`, `.editorconfig`, `.gitignore`, root `README`, `docker-compose.yml` for Postgres, pre-commit config, CI skeleton.
- **Definition of done**: `make bootstrap` succeeds on a clean clone; CI green on a no-op PR.
- **Estimate**: 6–8 h.
- **Dependencies**: none.
- **Risks**: monorepo tooling decisions (npm workspaces vs pnpm filter).

### Phase 2 — Backend Foundation
- **Deliverables**: FastAPI app factory, settings, structlog, request-id middleware, exception handlers, SQLAlchemy 2.0 async engine, Alembic init, base model with timestamps + UUID, `/health` endpoint, pytest scaffolding.
- **Definition of done**: `/health` returns 200; first Alembic revision created and applied; `pytest` runs and passes.
- **Estimate**: 8–10 h.
- **Dependencies**: Phase 1.
- **Risks**: async session/transaction patterns.

### Phase 3 — Authentication
- **Deliverables**: `User`, `RefreshToken` models; signup/login/refresh/logout endpoints; bcrypt hashing; JWT issuance with rotation; rate limiting on `/auth/*`; tests covering golden + reuse-detection paths.
- **Definition of done**: full auth flow + reuse-detection verified; coverage on `auth_service` ≥ 90%.
- **Estimate**: 12–16 h.
- **Dependencies**: Phase 2.
- **Risks**: refresh-rotation correctness; cookie SameSite cross-browser.

### Phase 4 — Project & Member Module
- **Deliverables**: `Project`, `ProjectMember` models; CRUD endpoints; RBAC dependencies; invitation flow (existing users); soft delete; ActivityLog model + writes.
- **Definition of done**: matrix of (role × action) covered by integration tests; last-admin/owner rules enforced.
- **Estimate**: 12–14 h.
- **Dependencies**: Phase 3.
- **Risks**: RBAC dependency composition; 404-vs-403 discipline.

### Phase 5 — Task Module
- **Deliverables**: `Task` model; CRUD + status patch endpoints; FSM enforcement; filter/sort/paginate; activity logging for every mutation; assignee validation.
- **Definition of done**: FSM exhaustive tests; pagination + filter contract tested.
- **Estimate**: 12–14 h.
- **Dependencies**: Phase 4.
- **Risks**: optimistic-concurrency design and adoption.

### Phase 6 — Frontend Foundation
- **Deliverables**: Vite + React + TS scaffold; Tailwind; React Router; Axios client + auth interceptor; Zustand auth slice; TanStack Query setup; design-system primitives (Button, Input, Card, Toast); ProtectedRoute; Auth pages (Signup, Login).
- **Definition of done**: golden auth flow works end-to-end against local backend; lint + typecheck green.
- **Estimate**: 14–18 h.
- **Dependencies**: Phase 3 + 5 (API contracts stable).
- **Risks**: axios refresh-token race; cookie behavior in dev across ports.

### Phase 7 — Projects, Tasks, Dashboard UI
- **Deliverables**: Project list/detail; Member management UI; Task list/board/detail; Task create/edit forms; Dashboard with stat cards + my-tasks + recent-activity; empty/error/loading states everywhere.
- **Definition of done**: Lighthouse Performance ≥ 90 on Projects page; axe-core clean.
- **Estimate**: 20–24 h.
- **Dependencies**: Phase 6.
- **Risks**: scope creep on board UX.

### Phase 8 — Testing & QA
- **Deliverables**: ≥ 80% backend coverage; component tests for critical UI; Playwright covering signup → project → invite → task → done.
- **Definition of done**: coverage gates in CI; nightly E2E green.
- **Estimate**: 10–12 h.
- **Dependencies**: Phase 7.
- **Risks**: flaky E2E; mitigate via stable test data + waitFor patterns.

### Phase 9 — Deployment & Polish
- **Deliverables**: Railway api + web services; managed Postgres; env vars; sentry; production checklist (Section 32) passing; README screenshots; demo seed script.
- **Definition of done**: live URL; production checklist 100% checked; rollback rehearsed.
- **Estimate**: 8–10 h.
- **Dependencies**: Phase 8.
- **Risks**: first-deploy CORS / cookie domain misconfig; do a staging rehearsal.

**Total estimate: 102–126 hours (~3 weeks for one senior engineer; ~6 weeks for one mid-level engineer).**

---

## 30. Suggested Folder Structure

### 30.1 Root Monorepo

```txt
team-task-manager/
├── apps/
│   ├── api/                    # FastAPI backend (Section 12)
│   └── web/                    # React frontend (Section 13)
├── packages/
│   └── shared-types/           # (optional) generated TS types from OpenAPI
├── docs/
│   ├── adr/
│   │   ├── 0001-monorepo.md
│   │   ├── 0002-pagination-strategy.md
│   │   └── 0003-jwt-strategy.md
│   ├── runbooks/
│   │   ├── deploy.md
│   │   ├── rollback.md
│   │   └── secret-rotation.md
│   └── img/
├── scripts/
│   ├── seed.py                 # seed demo data
│   ├── generate-openapi.sh
│   └── reset-db.sh
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── e2e.yml
│   │   └── deploy.yml
│   ├── CODEOWNERS
│   └── pull_request_template.md
├── docker-compose.yml          # local Postgres + Redis
├── Makefile
├── .editorconfig
├── .gitignore
├── .pre-commit-config.yaml
├── CLAUDE.md
├── SPECIFICATION.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### 30.2 CI/CD (`.github/workflows/ci.yml` skeleton)

```yaml
name: CI
on: [pull_request, push]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_PASSWORD: postgres }
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 5s
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
        working-directory: apps/api
      - run: uv run alembic upgrade head
        working-directory: apps/api
        env: { DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/postgres }
      - run: uv run ruff check .
        working-directory: apps/api
      - run: uv run black --check .
        working-directory: apps/api
      - run: uv run mypy .
        working-directory: apps/api
      - run: uv run pytest --cov=app --cov-fail-under=80
        working-directory: apps/api
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
        working-directory: apps/web
      - run: pnpm lint
        working-directory: apps/web
      - run: pnpm typecheck
        working-directory: apps/web
      - run: pnpm test --run
        working-directory: apps/web
      - run: pnpm build
        working-directory: apps/web
```

---

## 31. Python Environment & Tooling Setup

### 31.1 `apps/api/pyproject.toml`

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

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM", "RUF", "ASYNC"]
ignore = ["E501"]  # line length owned by black

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]

[tool.black]
line-length = 88
target-version = ["py312"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
mypy_path = "."
exclude = ["alembic/versions/"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["app"]

[tool.coverage.report]
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]
fail_under = 80
```

### 31.2 `uv` Workflow

- `uv venv` — create `.venv`.
- `uv add fastapi` — add to `pyproject.toml` + lockfile in one step.
- `uv sync --frozen` — production install; honors lockfile.
- `uv lock --upgrade-package fastapi` — controlled bumps.
- `uv run pytest` — runs in the project venv without activating it.

### 31.3 Alembic Setup

- Async-aware `env.py`:

```python
# alembic/env.py (excerpt)
from sqlalchemy.ext.asyncio import async_engine_from_config

def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        future=True,
    )
    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    asyncio.run(do_run())
```

- `target_metadata = Base.metadata` from `app.db.base`.
- Naming convention for constraints so autogenerate diffs are deterministic.

### 31.4 Standards Summary

| Standard | Tool | Enforcement |
|---|---|---|
| Formatting | `black` | pre-commit + CI |
| Linting | `ruff` | pre-commit + CI |
| Typing | `mypy --strict` | CI |
| Testing | `pytest` + coverage gate | CI |
| Dependency hygiene | `uv` lockfile + `pip-audit` | CI weekly |

---

## 32. Production Checklist

### Security
- [ ] All secrets via env vars; none committed.
- [ ] JWT secrets ≥ 32 random bytes.
- [ ] bcrypt rounds = 12 (or higher if benchmarked).
- [ ] CORS allow-list set explicitly (no `*`).
- [ ] HSTS, X-Content-Type-Options, X-Frame-Options headers set.
- [ ] Rate limits enabled on `/auth/*` and global.
- [ ] `/docs` and `/redoc` disabled (`DOCS_ENABLED=false`).
- [ ] Dependency audit clean (`pip-audit`, `pnpm audit`).
- [ ] No `dangerouslySetInnerHTML` in frontend code.
- [ ] Refresh-token rotation + reuse detection verified.

### Logging
- [ ] JSON logs in production.
- [ ] Every request has `request_id`.
- [ ] No PII (email, password, token) in any log line — verified via test.
- [ ] Sentry capturing both ends.

### Environment Validation
- [ ] All required env vars present (pydantic-settings validates at boot).
- [ ] `ENVIRONMENT=production`.
- [ ] `FRONTEND_URLS` matches deployed origin.
- [ ] `DATABASE_URL` uses `+asyncpg` driver.

### DB Migrations
- [ ] `alembic upgrade head` runs cleanly on a fresh DB.
- [ ] Migration runs before app start in deploy step.
- [ ] Failed migration halts deploy (verified once intentionally).
- [ ] Backups configured (Railway PG daily snapshots).

### Mobile Responsiveness
- [ ] Pages usable at 360 × 640 without horizontal scroll.
- [ ] Touch targets ≥ 44 × 44.
- [ ] Tested on real iOS Safari and Android Chrome.

### Railway Deployment
- [ ] `api` and `web` services deploy from `main`.
- [ ] Health check path `/health`; healthy within 5 s.
- [ ] Rollback procedure documented and rehearsed.
- [ ] Custom domain + TLS verified.

### API Validation
- [ ] OpenAPI generated and committed.
- [ ] Every endpoint has `response_model`.
- [ ] All errors conform to envelope schema.
- [ ] Pagination caps enforced (size ≤ 100).

### Lighthouse / Web Quality
- [ ] Performance ≥ 90.
- [ ] Accessibility ≥ 95 (axe-core no critical).
- [ ] Best Practices ≥ 90.
- [ ] SEO ≥ 80 (basic meta tags).

### Error Handling
- [ ] Frontend ErrorBoundary surfaces request-id.
- [ ] 4xx never logged at ERROR level.
- [ ] 5xx triggers Sentry alert.

### Health & Observability
- [ ] `/health` returns DB status.
- [ ] Railway metrics dashboards reviewed.
- [ ] Alerting policy: 5xx rate > 1% for 5 min → page.

---

**End of Specification — Version 1.0.0**

> _This document is a living artifact. Every meaningful architectural deviation in implementation must land alongside an ADR in `docs/adr/`._
