# ROADMAP — Task Manager API, 6 weeks to the job

Start: 2026-07-22 · Offer starts: ~2026-09-01

`CHALLENGE.md` = Week 1 (tickets 1–9). This file = Weeks 2–6, where it stops
being a tutorial project and becomes a real backend.

## Rules of engagement

- Every task gives you: **Goal → Search → Done when**. No code, no answers.
- "Search" = the exact terms to put into Django docs / Google. Read the **official
  docs first**, blog posts second. If a search term is unfamiliar, that's the point.
- Do the tasks **in order**. Each depends on the last.
- After each task: run it, commit it, paste me the diff. I review like a PR.
- **Never add a new model** until existing models are tested, permissioned, and
  query-profiled. Growth is vertical (layers), not horizontal (more CRUD).
- Stuck >30 min on one thing? Ask me. Stuck <30 min? Keep digging — that's where
  the learning is.

---

# Week 1 (Jul 22–28) — Foundations
**→ Work `CHALLENGE.md` tickets 1–9, in order.**

Current position: Ticket 1 incomplete (`Status` uses `models.Choices`, admin
unregistered, migration stale). Finish that before anything else.

**Week 1 exit bar:** authenticated CRUD, users see only their own data, task list
has no N+1, `manage.py test` passes with 3+ real tests.

---

# Week 2 (Jul 29–Aug 4) — Multi-tenancy & permissions
> This is where most real Django work actually lives.

### 2.1 — Membership model
**Goal:** A project has many members; a user belongs to many projects; each
membership carries a **role** (OWNER / ADMIN / MEMBER / VIEWER).
**Search:** `django ManyToManyField through model`, `django TextChoices`,
`django unique_together vs UniqueConstraint`
**Done when:** A user can be added to a project with a role; the same user cannot
be added to the same project twice (enforced at the **database** level, not just
in a serializer).

### 2.2 — Backfill without breaking data
**Goal:** Existing projects must get an OWNER Membership row for their current owner.
**Search:** `django data migration RunPython`, `django migrations reverse_code`
**Done when:** A migration creates the rows, and `migrate` then `migrate <app> <prev>`
both run clean. This is the single most job-relevant skill in Week 2.

### 2.3 — Custom permission classes
**Goal:** Replace queryset-scoping-only with real permissions. VIEWER can read,
MEMBER can edit tasks, ADMIN can manage members, OWNER can delete the project.
**Search:** `DRF BasePermission has_permission has_object_permission`,
`DRF get_object permission check`
**Done when:** Each role gets the right 200/403 on each verb. Know the difference
between `has_permission` and `has_object_permission` and *when each fires*.

### 2.4 — 403 vs 404
**Goal:** Decide, deliberately, whether a non-member hitting someone else's project
gets 403 or 404 — and be able to defend the choice.
**Search:** `403 vs 404 information leakage REST API`
**Done when:** Behavior is consistent everywhere and a test asserts it.

### 2.5 — Nested routes
**Goal:** `/api/projects/<id>/tasks/` alongside the flat task list.
**Search:** `drf-nested-routers`, `DRF ViewSet get_queryset url kwargs`
**Done when:** Nested list is scoped to that project and permission-checked.

**Week 2 exit bar:** Four roles, enforced by real permission classes, proven by tests.

---

# Week 3 (Aug 5–11) — Postgres & data integrity
> The junior→mid line. Most people skip this. Don't.

### 3.1 — Move off SQLite
**Goal:** Run Postgres locally, config from environment variables.
**Search:** `docker compose postgres`, `django-environ`, `dj-database-url`
**Done when:** App runs on Postgres, `settings.py` contains **zero** secrets, and
`.env` is gitignored.

### 3.2 — Constraints in the database
**Goal:** Business rules the ORM can't bypass. E.g. a task's `due_date` can't precede
its project's `created_at`; status must be a valid value.
**Search:** `django models CheckConstraint`, `django Meta constraints`
**Done when:** Violating it from `manage.py shell` raises `IntegrityError`. Know why
serializer validation alone is not enough.

### 3.3 — Indexes, measured
**Goal:** Stop guessing about performance.
**Search:** `django Meta indexes`, `postgres EXPLAIN ANALYZE`, `django queryset .explain()`
**Done when:** You seed ~50k tasks, run `.explain()` on your filtered list query,
add the index, and can state the before/after — sequential scan vs index scan.

### 3.4 — Transactions & races
**Goal:** Two simultaneous requests must not corrupt state.
**Search:** `django transaction.atomic`, `select_for_update`, `ATOMIC_REQUESTS`
**Done when:** You can explain a concrete race in your API and show the code that
closes it.

### 3.5 — Query profiling as a habit
**Search:** `django-debug-toolbar`, `django assertNumQueries`
**Done when:** A test **fails** if a list endpoint's query count regresses.

**Week 3 exit bar:** Postgres, DB-level constraints, a measured index win, and
query-count tests guarding against N+1.

---

# Week 4 (Aug 12–18) — Async, caching, throttling
> Most bootcamp grads never touch this. It's a real differentiator.

### 4.1 — Celery + Redis
**Goal:** Work that happens outside the request/response cycle.
**Search:** `celery django first steps`, `celery broker redis`, `django celery worker`
**Done when:** Creating a task queues a job that logs something, and you can watch
the worker consume it.

### 4.2 — A real async job
**Goal:** Email/notify assignees about tasks due tomorrow.
**Search:** `celery beat periodic task`, `django send_mail console backend`
**Done when:** A scheduled job finds due tasks and "sends". Know why this must not
run inside the web request.

### 4.3 — Retries & idempotency
**Goal:** Jobs fail. Handle it.
**Search:** `celery autoretry_for retry_backoff`, `idempotent task design`
**Done when:** A deliberately failing task retries with backoff and doesn't
double-send on retry.

### 4.4 — Caching
**Search:** `django cache framework redis`, `django cache_page`, `cache invalidation django signals`
**Done when:** An expensive endpoint is cached and correctly invalidated on write.
Prove the hit/miss with query counts.

### 4.5 — Throttling
**Search:** `DRF throttling ScopedRateThrottle`
**Done when:** Hammering the login endpoint returns 429.

**Week 4 exit bar:** A worker, a scheduled job, a cache with correct invalidation,
and rate limits.

---

# Week 5 (Aug 19–25) — Production
> This is what your first month on the job will actually feel like.

### 5.1 — Dockerize
**Search:** `dockerfile python multi-stage build`, `gunicorn django`, `docker compose django postgres redis`
**Done when:** `docker compose up` gives a working API with no local Python needed.

### 5.2 — CI
**Search:** `github actions django postgres service`, `github actions run tests on PR`
**Done when:** Every push runs migrations + the full test suite, and a failing test
blocks the merge.

### 5.3 — Production settings audit
**Search:** `django deployment checklist`, `manage.py check --deploy`, `django settings split by environment`
**Done when:** `check --deploy` is clean: `DEBUG=False`, `ALLOWED_HOSTS`,
`SECURE_*` headers, secret from env.

### 5.4 — Observability
**Search:** `django LOGGING configuration dictConfig`, `sentry django integration`,
`structured logging json python`
**Done when:** Errors carry request context, and you can find one specific request
in the logs. "It broke" must be debuggable without a debugger.

### 5.5 — Deploy it
**Search:** `deploy django render`, `railway django`, `fly.io django`
**Done when:** A public URL serves your API, migrations ran on a live DB, static
files work.

### 5.6 — Zero-downtime migration drill
**Goal:** Rename a field on a table with live data without downtime.
**Search:** `zero downtime django migrations`, `expand contract migration pattern`,
`postgres lock ALTER TABLE`
**Done when:** You can explain the multi-deploy expand/contract sequence and why the
naive rename causes an outage. **Ask about this in interviews — it signals seniority.**

**Week 5 exit bar:** Containerized, CI-gated, deployed, observable, and you
understand migration safety.

---

# Week 6 (Aug 26–Sep 1) — API maturity + first-day readiness

### 6.1 — OpenAPI docs
**Search:** `drf-spectacular`, `openapi schema DRF`
**Done when:** `/api/schema/swagger-ui/` documents every endpoint accurately.

### 6.2 — Versioning
**Search:** `DRF versioning URLPathVersioning`, `REST API breaking change strategy`
**Done when:** Routes live under `/api/v1/` and you can describe how you'd ship v2
without breaking v1 clients.

### 6.3 — Audit log
**Search:** `django signals post_save`, `django-simple-history`, `audit log design`
**Done when:** Status changes are recorded with who + when. Know the tradeoff
between signals and explicit service functions — and why many seniors dislike signals.

### 6.4 — README that gets you hired
**Done when:** Architecture overview, ER diagram, setup in ≤3 commands, auth flow,
and a short "decisions & tradeoffs" section. That last section is what senior
readers actually read.

### 6.5 — Explain it out loud
**Done when:** You can explain, without notes, in under 5 minutes each:
- Request → response lifecycle in Django (middleware, URL resolution, view, serializer)
- Why `select_related` and `prefetch_related` differ, and when each applies
- Your permission model and where each check fires
- What happens on `POST /api/auth/token/`, byte to byte
- Why `AUTH_USER_MODEL` exists instead of importing `User`

**Week 6 exit bar:** Documented, versioned, deployed — and you can defend every
decision in it.

---

## Progress log
<!-- date — what I finished — what I got wrong -->
-
</content>
