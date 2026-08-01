# Django Backend — Day 1 Cheat Sheet

Read this over coffee tomorrow. It covers everything you built tonight + how to
read and run someone else's Django project. Examples use YOUR `Note` API so it's familiar.
Written in Spring Boot terms where useful.

---

## 0. The one-paragraph mental model

A **project** is the whole app + config (`config/`). It contains **apps** — pluggable
feature modules (`accounts/`, `tasks/`). Each app has **models** (DB tables), and for an
API you add **serializers** (JSON converters) + **viewsets** (CRUD logic) + **urls** (routes).
Django's **ORM** talks to the DB in Python instead of SQL. **Migrations** turn model
changes into versioned DB changes. That's 90% of the job.

---

## 1. Daily terminal ritual (do this EVERY new terminal)

```bash
cd /path/to/project          # 1. go to the project (manage.py lives here)
source venv/bin/activate      # 2. activate venv → prompt shows (venv)
# on my Mac only: unalias python   (or just use python3 below)
python manage.py runserver    # 4. run at http://127.0.0.1:8000
```
- Forgot step 2? You'll get `ModuleNotFoundError: No module named 'django'`. That error
  literally means "wrong Python — activate the venv."
- At a real job, start-of-day is: `git pull` → `pip install -r requirements.txt`
  (if deps changed) → `python manage.py migrate` (if migrations were added) → `runserver`.

---

## 2. Spring Boot → Django translation table

| Spring Boot | Django | Notes |
|---|---|---|
| `pom.xml` / Gradle | `requirements.txt` + `pip` + venv | PyPI ≈ Maven Central |
| Whole app | **project** (`config/`) | Holds settings + root urls |
| Feature module/package | **app** (`accounts/`) | A project has many apps |
| `application.properties` | `settings.py` | All config, in Python |
| `@Entity` | **Model** (`models.py`) | Also auto-generates migrations |
| JPA / Hibernate | **Django ORM** | Built-in, no setup |
| `JpaRepository<Note>` | `Note.objects` (default Manager) | Free per model |
| Flyway / Liquibase | **Migrations** | Django writes them for you |
| `@RestController` | **ViewSet** / View | `ModelViewSet` = full CRUD |
| DTO + Jackson + Bean Validation | **Serializer** | Convert + validate in one |
| `@RequestMapping` | **urls.py** + Router | Router auto-wires CRUD routes |
| `toString()` | `__str__()` | How an object shows as text |
| `new Foo()` | `Foo()` | Forgetting `()` → "missing self" errors |
| `mvn spring-boot:run` | `manage.py runserver` | Dev server, auto-reload |

---

## 3. The full pipeline (what you built)

```
Model → makemigrations → migrate → DB table
  → register in admin (optional)
  → Serializer (model ⇄ JSON)
  → ViewSet (CRUD logic)
  → Router in urls.py (routes)
  → live JSON API at /api/notes/
```
Every backend feature follows this exact path. Learn the path, not the specifics.

---

## 4. Models (the data layer)

`accounts/models.py`:
```python
from django.db import models

class Note(models.Model):
    title = models.CharField(max_length=50)   # short text (VARCHAR) — needs max_length
    body  = models.TextField()                # long text (TEXT), no length limit

    def __str__(self):        # human-readable label (like Java toString())
        return self.title     # return the SHORT identifying field, not the payload
```
Common field types:
- `CharField(max_length=...)` — short string
- `TextField()` — long string
- `IntegerField()`, `BooleanField()`, `DateTimeField(auto_now_add=True)`
- `ForeignKey(OtherModel, on_delete=models.CASCADE)` — many-to-one (like `@ManyToOne`)
- `ManyToManyField(OtherModel)` — many-to-many

You never write an `id` field — Django adds an auto primary key automatically.

---

## 5. Migrations (versioned DB changes)

```bash
python manage.py makemigrations   # reads models → writes a migration FILE (doesn't touch DB)
python manage.py migrate          # applies migration files → changes the actual DB
```
- `makemigrations` = "record the plan." `migrate` = "execute the plan."
- Migration files live in `app/migrations/` and are committed to git — teammates run
  `migrate` to get the same schema. (This is Flyway/Liquibase, but auto-written.)
- **Rule:** every time you change a model, run both commands.

---

## 6. The ORM / QuerySets (you'll READ these all day)

`Model.objects` is the gateway to the DB (your free `JpaRepository`). Examples:
```python
Note.objects.all()                        # SELECT * FROM note        → QuerySet (0..many)
Note.objects.count()                      # how many rows
Note.objects.create(title="x", body="y")  # INSERT (build + save in one)
Note.objects.get(id=1)                    # SELECT one by PK — ERRORS if 0 or 2+ matches
Note.objects.filter(title="x")            # WHERE title = 'x'         → QuerySet (0..many)
Note.objects.exclude(title="x")           # WHERE title != 'x'
Note.objects.filter(title__icontains="sh")# WHERE title ILIKE '%sh%'  (case-insensitive)
Note.objects.order_by("-id")              # ORDER BY id DESC

n = Note.objects.get(id=1); n.title = "new"; n.save()   # UPDATE
n.delete()                                              # DELETE
```
**`.get()` vs `.filter()`** — the #1 thing to internalize:
- `.get()` → exactly ONE object. 0 matches → raises `DoesNotExist`; 2+ → `MultipleObjectsReturned`.
  (≈ `findById().orElseThrow()`)
- `.filter()` → a QuerySet of 0..many. "None found" is fine, returns empty. (≈ `findByX() -> List`)

**Field lookups** (the `field__lookup=value` syntax = SQL WHERE):
`__gte` ≥, `__lte` ≤, `__gt` >, `__lt` <, `__in=[...]`, `__contains` (LIKE),
`__icontains` (ILIKE), `__startswith`, `__isnull=True`.

**Performance (senior will ask):** `select_related("fk_field")` (JOIN, for ForeignKey) and
`prefetch_related("m2m_field")` avoid the **N+1 query problem** — one query per row in a loop.
If you see a loop doing `for x in qs: x.author.name`, that's a red flag without `select_related`.

---

## 7. DRF — the three pieces of an API

### Serializer (`serializers.py`) — model ⇄ JSON + validation
```python
from rest_framework import serializers
from .models import Note

class NoteSerializer(serializers.ModelSerializer):
    class Meta:                          # MUST be exactly "Meta" (case-sensitive!)
        model = Note
        fields = ["id", "title", "body"] # which fields to expose as JSON
```
`ModelSerializer` reads the model and builds fields + validation for you (like Lombok+Jackson).

### ViewSet (`views.py`) — CRUD logic
```python
from rest_framework import viewsets, permissions
from .models import Note
from .serializers import NoteSerializer

class NoteViewSet(viewsets.ModelViewSet):        # = full CRUD: list/create/retrieve/update/delete
    queryset = Note.objects.all()                # data it operates on
    serializer_class = NoteSerializer            # how to convert to/from JSON
    permission_classes = [permissions.AllowAny]  # open (TEMP — lock down with JWT in prod)
```
One `ModelViewSet` = a whole REST resource. That's the payoff over Spring's 5 mapped methods.

### Router (`urls.py`) — auto-generates routes
```python
from rest_framework.routers import DefaultRouter
from .views import NoteViewSet

router = DefaultRouter()                  # NOTE the () — it's an object, not the class!
router.register(r"notes", NoteViewSet)    # creates /notes/ and /notes/<id>/ automatically
urlpatterns = router.urls
```
Then wire it into the root `config/urls.py`:
```python
from django.urls import path, include
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),   # → /api/notes/
]
```
Endpoints you get for free:
- `GET  /api/notes/`      → list      | `POST   /api/notes/`      → create
- `GET  /api/notes/1/`    → retrieve  | `PUT/PATCH /api/notes/1/` → update
- `DELETE /api/notes/1/`  → delete

Visit `/api/notes/` in a browser → DRF's **browsable API** (a web UI over your JSON).

---

## 8. Auth & permissions (the shape of it)

- `AUTH_USER_MODEL = "accounts.User"` in settings → use a **custom user** (set BEFORE first migrate).
- Global default (in `settings.py REST_FRAMEWORK`): `DEFAULT_PERMISSION_CLASSES` +
  `DEFAULT_AUTHENTICATION_CLASSES`. A view can override with its own `permission_classes`.
- Common permissions: `AllowAny`, `IsAuthenticated`, `IsAdminUser`, or custom `IsOwner...`.
- **JWT** (SimpleJWT): client POSTs username/password to a token endpoint → gets an
  `access` + `refresh` token → sends `Authorization: Bearer <access>` on each request.
  (≈ Spring Security with JWT filter.)

---

## 9. Settings essentials (`settings.py`)

| Setting | What it does | Gotcha |
|---|---|---|
| `DEBUG` | dev mode (detailed errors) | **`False` = production.** Never browse locally with it off |
| `ALLOWED_HOSTS` | whitelist of host names | With `DEBUG=False`, must list hosts or you get **400 Bad Request** |
| `INSTALLED_APPS` | which apps/libraries are active | Add your app + `rest_framework` here or nothing works |
| `AUTH_USER_MODEL` | your custom user | Set before first migration |
| `DATABASES` | which DB | sqlite for dev, PostgreSQL for real |
| `SECRET_KEY` | crypto key | In prod: load from env var, never commit |

---

## 10. Errors you already hit (and what they mean)

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'django'` | venv not activated / wrong Python | `source venv/bin/activate` (or use `python3`) |
| `Bad Request (400)` on localhost | `DEBUG=False` + host not in `ALLOWED_HOSTS` | `DEBUG=True` for dev; add `127.0.0.1` |
| `register() missing 1 required positional argument: 'self'` | called method on a class, forgot `()` | `DefaultRouter()` not `DefaultRouter` |
| `Class X missing 'Meta' attribute` | typo'd inner `class Meta` | must be exactly `Meta` |
| Admin shows `Note object (1)` | no `__str__` | add `def __str__: return self.title` |

---

## 11. How to READ an unfamiliar Django project (tomorrow's real skill)

Open files in this order — big picture → detail:
1. **`requirements.txt`** → what libraries/shape (DRF? Celery? Postgres?)
2. **`settings.py`** → `INSTALLED_APPS`, `DATABASES`, `AUTH_USER_MODEL`, `REST_FRAMEWORK`
3. **root `urls.py`** → the site map; follow each `include()` to an app's urls
4. **each app's `models.py`** → the domain/data model (understand this = understand 60%)
5. **`serializers.py` → `views.py`** → how data becomes JSON + what each endpoint does
6. **`migrations/`** → DB history, only if needed

**Trace-a-request drill** (understand ANY endpoint):
```
URL (urls.py) → View/ViewSet (views.py) → Serializer (serializers.py) → Model (models.py) → DB
```
Four hops. You built all four tonight, so you'll recognize them anywhere.

---

## 12. How to RUN someone else's project on your PC (literal Day-1 task)

```bash
git clone <repo-url>
cd <project>
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt        # install THEIR exact deps
cp .env.example .env                    # then ask a teammate for the real values
python manage.py migrate               # build your local DB
python manage.py createsuperuser       # optional, for admin
python manage.py runserver
```
- If it needs PostgreSQL: you already have it installed. A teammate gives you the DB name/creds.
- Errors here are NORMAL. They usually name what's missing (a package, an env var, a DB
  connection). Asking "what goes in `.env`?" on day one is expected, not weak.

---

## 13. One-line glossary

- **Project** = the whole app/config. **App** = a feature module inside it.
- **Model** = a DB table as a Python class. **Migration** = a versioned DB change.
- **ORM** = query the DB in Python. **QuerySet** = a lazy list of DB rows.
- **Manager** (`.objects`) = the query gateway per model.
- **Serializer** = model ⇄ JSON + validation. **ViewSet** = CRUD logic. **Router** = auto routes.
- **DRF** = Django REST Framework (the API layer). **JWT** = token auth.

---

You built a full model→migration→admin→ORM→serializer→viewset→router→API slice yourself.
Tomorrow: read their `urls.py` + `models.py`, trace one request, get the project running.
You've got the map. Good luck. 💪
```
