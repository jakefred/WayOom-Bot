# AGENTS.md — WayOom Developer Reference

A working reference for AI agents and developers contributing to this project.

---

## What this project is

WayOom is a self-hosted flashcard app (decks, cards, spaced review) built on Django + React. The goal is a personal memory tool that is accessible, satisfying, and easy to self-host. It is intentionally built on a well-understood, well-documented stack — no exotic dependencies, no vendor lock-in.

---

## Core principles

- **Never bypass ownership.** All reads go through `visible_to(user)`, all writes through `owned_by(user)`. Never write a raw, unscoped queryset.
- **Cards inherit deck privacy.** A card is only as visible as its parent deck.
- **UUID primary keys everywhere.** All models use UUIDs to prevent enumeration.
- **Secrets stay out of code.** All sensitive values come from environment variables (`.env` loaded via `python-dotenv`).
- **Security is not an afterthought.** JWT auth, ownership-scoped queries, and environment-based secrets are baked in from the start.

---

## Architecture

```
Client Request → Views → Serializers → QuerySets → Models → Database
```

- **Backend:** Django 6 + Django REST Framework. PostgreSQL in production, SQLite fallback for local dev (set `DB_NAME=""` to force SQLite).
- **Frontend:** Vite + React 19 + TypeScript + shadcn/ui. Dev server at `localhost:5173`, proxies `/api` to `localhost:8000`.
- **Auth:** Email-based login (no username field). 15-minute JWT access tokens held in memory; 7-day rotating refresh tokens in `localStorage`.

---

## Key files

| File | Purpose |
|------|---------|
| `backend/wayoom_bot/models.py` | `Deck`, `Card`, `DeckMedia` models + ownership querysets |
| `backend/wayoom_bot/views.py` | `DeckViewSet`, `CardViewSet`, `ApkgImportView`, `DeckMediaView` |
| `backend/wayoom_bot/serializers.py` | Serializers + media URL rewriting in `CardSerializer.to_representation()` |
| `backend/wayoom_bot/permissions.py` | `IsOwnerOrReadOnly` — blocks writes on non-owned objects |
| `backend/wayoom_bot/importers/apkg.py` | `.apkg` parser — supports `.anki2`, `.anki21`, `.anki21b` (zstd + protobuf) |
| `backend/wayoom_bot/tests.py` | Full test suite (166+ tests) |
| `frontend/src/api/decks.ts` | Typed fetch wrappers for decks, cards, import |
| `frontend/src/context/AuthContext.tsx` | JWT state, silent refresh, login/logout |
| `frontend/src/pages/DeckDetailPage.tsx` | Card list with DOMPurify HTML rendering |
| `frontend/src/pages/StudyPage.tsx` | Flashcard study mode — progressive reveal, dot indicators, keyboard nav |
| `frontend/src/pages/DeckListPage.tsx` | Deck list, create form, `.apkg` upload |
| `frontend/src/lib/sanitize.ts` | Shared `sanitizeCardHtml()` — DOMPurify config for card HTML |
| `backend/config/settings.py` | DB, JWT, DRF, OpenAPI, media storage config |

---

## Running the app

**Backend:**
```bash
cd backend
SECRET_KEY="dev" DB_NAME="" python manage.py migrate
SECRET_KEY="dev" DB_NAME="" python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Tests:**
```bash
cd backend
SECRET_KEY="dev" DB_NAME="" python manage.py test
```

**Migrations (SQLite, no Postgres required):**
```bash
cd backend
SECRET_KEY="dev" DB_NAME="" python manage.py makemigrations wayoom_bot --name <description>
```

---

## Changing model fields — required steps

See `docs/adding-model-fields.md` for the full annotated checklist.

---

## Common mistakes

| Symptom | Cause |
|---------|-------|
| `TypeError: Card() got unexpected keyword argument 'name'` | Field removed from model but still in a test `create()` call |
| `admin.E108: list_display refers to 'name'` | Field removed from model but still in `CardAdmin.list_display` |
| `IntegrityError: NOT NULL constraint` | Added a non-nullable field without a `default` on a table with existing rows |
| TypeScript build error on `card.name` | Field removed from `Card` interface but still referenced in a page component |
| Unscoped queryset returning another user's data | Used `Card.objects.filter(...)` instead of `Card.objects.owned_by(user)` |

---

## Patterns to follow

**Ownership queryset:**
```python
# Reads
deck = Deck.objects.visible_to(request.user).get(pk=pk)
# Writes
deck = Deck.objects.owned_by(request.user).get(pk=pk)
```

**Media URL rewriting** happens in `CardSerializer.to_representation()` — bare filenames in card HTML are resolved to `/api/decks/{id}/media/{filename}` at API time. Raw Anki HTML is kept clean in the database.

**Deduplication on import** — `parse_apkg()` uses deterministic UUID v5 keyed on source identifiers. Re-importing the same file silently skips existing records.

**Card HTML rendering** — card fields contain HTML from Anki imports. The frontend sanitizes via `sanitizeCardHtml()` from `src/lib/sanitize.ts` (DOMPurify with `<audio>` and `controls` added to the allowlist). Never render card HTML unsanitized. Both `DeckDetailPage` and `StudyPage` import from this shared utility.

**Frontend API calls** — all typed fetch wrappers in `src/api/` accept the JWT access token as a parameter and throw a human-readable `Error` on non-2xx responses. Follow this pattern for new endpoints.
