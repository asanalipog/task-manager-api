# Django in 1 Week — Task Manager API

Rebuilding my Spring Boot task manager as a Django + DRF REST API.
Goal: job-ready backend familiarity. Learn by building. One project, grown daily.

**Terminal note:** `python` is aliased to system Python. After `source venv/bin/activate`,
use `python3 manage.py ...` (or run `unalias python`).

---

## Day 1 — Setup & foundations ⏳
- [x] venv + install Django, DRF, SimpleJWT, django-environ, psycopg2
- [x] `startproject config .` + `startapp accounts`
- [x] Custom user model (`accounts.User`) set BEFORE first migration
- [x] settings: INSTALLED_APPS, AUTH_USER_MODEL, REST_FRAMEWORK
- [ ] Run first migration + create superuser + start server  ← YOU
- [ ] Understand: project vs app, settings.py, manage.py, request→response flow

## Day 2 — URLs, Views, Models
- [ ] URL routing (patterns, path converters, named URLs, reverse)
- [ ] Function-based vs class-based views
- [ ] Core models: Project, Task, Membership (write these yourself)
- [ ] makemigrations / migrate discipline

## Day 3 — ORM deep-dive + Admin
- [ ] Querying: filter/exclude/get, lookups, relationships
- [ ] N+1, select_related / prefetch_related
- [ ] Django admin customization

## Day 4 — Auth + DRF part 1
- [ ] Serializers, ModelSerializer, APIView
- [ ] First JSON endpoints for tasks
- [ ] (optional, ~30 min) HTML basics review — read/understand only, not build. See LEARN.md links (MDN first). Context for front↔back interaction + DRF browsable API

## Day 5 — DRF part 2 (the core job skill)
- [ ] ViewSets + Routers, full CRUD
- [ ] JWT auth (login/refresh), permissions (IsOwner...)
- [ ] Pagination, filtering

## Day 6 — Testing + config/security
- [ ] pytest-django: tests for models + API
- [ ] Env vars/secrets, DEBUG=False, PostgreSQL, production checklist

## Day 7 — Deploy + interview review
- [ ] Docker/Gunicorn OR deploy to Render/Railway
- [ ] GitHub repo + clean README
- [ ] Explain: request lifecycle, ORM, serializers, auth flow
