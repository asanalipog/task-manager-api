# CHALLENGE — Task Manager API (the real thing)

This is a graded, ticket-style challenge. Work top to bottom. Each ticket has:
**Goal → Hints → Acceptance criteria (AC)**. You write the code; I review.
Don't jump ahead — each ticket builds on the last. Commit after each one.

Rebuild your Spring Boot task manager as a Django REST API. Put it in a NEW app
called `projects` (`python manage.py startapp projects`, add to INSTALLED_APPS).
Leave `Note` alone — it was practice.

Difficulty: 🟢 core (must do) · 🟡 real-job · 🔴 senior. Get as far as you can.

---

## 🟢 Ticket 1 — Model the domain
**Goal:** Two related models with a real relationship, choices, and timestamps.

**Hints:**
- `Project`: `name` (CharField), `description` (TextField, `blank=True`), `owner`
  (ForeignKey to the user model — use `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`,
  `related_name="projects"`), `created_at` (`DateTimeField(auto_now_add=True)`).
- `Task`: `title`, `description` (blank), `project` (ForeignKey → Project,
  `related_name="tasks"`), `assignee` (ForeignKey → user, `null=True, blank=True`),
  `status`, `priority`, `due_date` (`DateField`, null/blank ok), `created_at`.
- For `status`, use **choices**. Look up `models.TextChoices` (e.g. TODO/IN_PROGRESS/DONE)
  and give the field a `default`.
- Add `__str__` to both.
- Import the user model correctly: `from django.conf import settings` → reference
  `settings.AUTH_USER_MODEL` (NOT a direct import of your User class — this is the correct pattern).

**AC:**
- [ ] `makemigrations` + `migrate` run clean.
- [ ] In the admin (register both), you can create a Project, then a Task linked to it.
- [ ] A Task's `status` shows a dropdown with your choices.

> Spring: these are your `@Entity` classes with `@ManyToOne` (project, assignee) and an enum.

---

## 🟢 Ticket 2 — Serializers + ViewSets + routes
**Goal:** Full CRUD JSON API for both models at `/api/projects/` and `/api/tasks/`.

**Hints:**
- `ProjectSerializer` and `TaskSerializer` as `ModelSerializer`s. Expose sensible fields.
- For now, make `owner` **read-only** on ProjectSerializer (the API shouldn't let the
  client pick the owner — we'll set it from the logged-in user in Ticket 4). Look up
  `read_only_fields` in the serializer's `Meta`.
- `ModelViewSet` for each; wire with a `DefaultRouter` in `projects/urls.py`, include under `api/`.

**AC:**
- [ ] `GET/POST /api/projects/` and `/api/tasks/` work in the browsable API.
- [ ] Creating a Task lets you pick a Project (you'll see a dropdown of project IDs).

---

## 🟡 Ticket 3 — JWT authentication
**Goal:** Real token auth. No more `AllowAny`.

**Hints:**
- Remove the `AllowAny` overrides. Your global default is already `IsAuthenticated` + JWT.
- Add SimpleJWT's token endpoints to your urls:
  `from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView`
  → `path("api/auth/token/", TokenObtainPairView.as_view())` and `.../token/refresh/`.
- Test the flow: POST your superuser's username+password to `/api/auth/token/` → you get
  `access` + `refresh`. Then call `/api/projects/` sending header
  `Authorization: Bearer <access>`. Use the browsable API + a tool (curl / httpie / Postman).

**AC:**
- [ ] `/api/projects/` returns **401** with no token.
- [ ] POSTing credentials to `/api/auth/token/` returns an access token.
- [ ] With `Authorization: Bearer <token>`, `/api/projects/` returns data.

> Spring: this is Spring Security + a JWT filter — but ~6 lines instead of a config class.

---

## 🟡 Ticket 4 — Ownership (the big one)
**Goal:** Users only see and manage **their own** projects. The owner is set automatically.

**Hints:**
- **Auto-set owner on create:** override `perform_create(self, serializer)` in the
  ProjectViewSet → `serializer.save(owner=self.request.user)`.
- **Scope the list:** override `get_queryset(self)` to return
  `Project.objects.filter(owner=self.request.user)` — so users never see others' projects.
- Do the analogous thing for Tasks (scope tasks to projects the user owns —
  `Task.objects.filter(project__owner=self.request.user)` — note the `__` spanning the FK!).

**AC:**
- [ ] Create 2 users. Each only sees their own projects in `GET /api/projects/`.
- [ ] You never send `owner` in the POST body, yet the created project is owned by you.
- [ ] User A gets 404/empty trying to access User B's project by id.

---

## 🟡 Ticket 5 — Filtering, ordering, pagination
**Goal:** Query the API like a real client would.

**Hints:**
- Add pagination in `settings.REST_FRAMEWORK`: `DEFAULT_PAGINATION_CLASS` =
  `rest_framework.pagination.PageNumberPagination`, `PAGE_SIZE` = 10.
- `pip install django-filter`, add `"django_filters"` to INSTALLED_APPS and to
  `DEFAULT_FILTER_BACKENDS`. Then on TaskViewSet set `filterset_fields = ["status", "project"]`
  and `ordering_fields = ["due_date", "priority"]` (add `OrderingFilter`).

**AC:**
- [ ] `GET /api/tasks/?status=TODO` returns only TODO tasks.
- [ ] `GET /api/tasks/?ordering=due_date` sorts by due date.
- [ ] List responses are paginated (`count`, `next`, `previous`, `results`).

---

## 🔴 Ticket 6 — Custom action
**Goal:** An endpoint that isn't plain CRUD: mark a task done.

**Hints:**
- In TaskViewSet, use `@action(detail=True, methods=["post"])` (import from `rest_framework.decorators`).
- Define `def complete(self, request, pk=None):` → get the task (`self.get_object()`),
  set `status = DONE`, `save()`, return a `Response(...)`.
- This auto-creates the route `POST /api/tasks/<id>/complete/`.

**AC:**
- [ ] `POST /api/tasks/1/complete/` flips that task's status to DONE and returns it.

---

## 🔴 Ticket 7 — Validation (business rules)
**Goal:** Reject bad data with a clear 400, not a 500.

**Hints (pick at least one):**
- On `TaskSerializer`, add `def validate_due_date(self, value):` → raise
  `serializers.ValidationError("Due date can't be in the past")` if it's before today.
- Or a cross-field `def validate(self, attrs):` → an assignee must be the project owner
  (or later, a member). Raise `ValidationError` if not.

**AC:**
- [ ] POSTing a task with a past `due_date` returns **400** with your message, not a crash.

---

## 🔴 Ticket 8 — Kill the N+1 (performance)
**Goal:** One query for the list, not one-per-row.

**Hints:**
- Your task list touches `task.project` and `task.assignee` per row → N+1.
- In `get_queryset`, add `.select_related("project", "assignee")`.
- Prove it: install `django-debug-toolbar` OR wrap a shell loop with
  `from django.db import connection; print(len(connection.queries))` before/after.

**AC:**
- [ ] Query count for the task list is roughly constant regardless of row count.

---

## 🔴 Ticket 9 — Tests
**Goal:** Prove it works, automatically. This is what makes you hireable, not just able.

**Hints:**
- Use DRF's `APITestCase` (or `pip install pytest-django`). Create a user, authenticate
  (`self.client.force_authenticate(user=...)`), then assert on responses.
- Write at least: (a) unauthenticated request → 401; (b) create a project → 201 and
  owner is the caller; (c) user A can't see user B's project.

**AC:**
- [ ] `python manage.py test` passes with 3+ meaningful tests.

---

## Stretch (if you're flying) 🚀
- `Comment` model on tasks (FK task + author) with nested serializer.
- Project membership (ManyToMany users) so assignees must be members.
- `IsOwnerOrReadOnly` custom permission class instead of only queryset scoping.
- Swagger/OpenAPI docs via `drf-spectacular`.

---

### How to work this
Do one ticket, run it, commit (`git commit -m "ticket N: ..."`), paste me the code.
I'll review it like a PR before you move on. Ticket 4 (ownership) is where it stops being
a toy and starts being a real backend — get there and you'll understand what the job is.
```
