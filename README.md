# WayOom

A long-term memory tool designed to be accessible, satisfying to use, and easy to self-host.

WayOom starts as a flashcard app — decks, cards, spaced review — but the vision is broader: a personal memory layer that helps you hold onto what you learn. The kind of tool you open because it works, not because you have to.

---

## Philosophy

- **Start small, scale when you need to.** The app runs on SQLite and a single dev server today. When it's time to go live, swap in PostgreSQL, add a reverse proxy, and deploy — no rewrite required.
- **Accessible by default.** The UI is built on [shadcn/ui](https://ui.shadcn.com/) for accessible, consistent components. The goal is a clean experience that feels good on desktop and mobile.
- **Own your stack.** Django + React is a well-understood, well-documented foundation. No exotic dependencies, no vendor lock-in. You can fork it, extend it, or host it yourself.
- **Security is not an afterthought.** UUID primary keys, ownership-scoped queries, JWT authentication, and environment-based secrets are baked in from the start — not bolted on later.

---

## Project Structure

```
WayOom Bot/
├── backend/
│   ├── config/          # Django project settings, URLs, WSGI/ASGI
│   ├── users/           # Custom user model (email-based login)
│   ├── wayoom_bot/      # Core app — models, views, serializers, importers
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Vite + React + TypeScript + shadcn/ui
└── docs/
```

---

## Getting Started

### Backend

**Prerequisites:** Python 3.12+

1. **Clone and set up**

   ```bash
   git clone https://github.com/jakefred/WayOom-Bot.git
   cd "WayOom Bot"
   python -m venv backend/.venv
   # Windows: backend\.venv\Scripts\activate
   # macOS/Linux: source backend/.venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp backend/.env.example backend/.env
   ```

   Edit `backend/.env` with your values. Generate a `SECRET_KEY`:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   **PostgreSQL:** Set `DB_NAME`, `DB_USER`, `DB_PASSWORD` in `.env`. If `DB_NAME` is unset, the app falls back to SQLite. `.env` is loaded automatically via `python-dotenv`.

3. **Run**

   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

   API: `http://127.0.0.1:8000/` | Admin: `http://127.0.0.1:8000/admin/`

### Frontend

**Prerequisites:** Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. Requests to `/api` are proxied to the Django backend.

### API Documentation

Available when `DEBUG=True`:

| URL | Description |
|-----|-------------|
| `/api/schema/swagger-ui/` | Interactive Swagger UI |
| `/api/schema/redoc/` | ReDoc documentation |
| `/api/schema/` | Raw OpenAPI 3.0 schema |

See [`backend/README.md`](backend/README.md) for full endpoint reference.

---

## Architecture

```
Client Request → Views → Serializers → QuerySets → Models → Database
```

- **Email-based auth** — custom user model, no username field.
- **UUID primary keys** on all models to prevent enumeration.
- **Ownership-scoped queries** — `visible_to(user)` for reads, `owned_by(user)` for writes. Never raw, unscoped queries.
- **Cards inherit deck privacy** — a card is only as visible as its parent deck.
- **Secrets stay out of code** — all sensitive values from environment variables.

---

## Roadmap

### Done

- [x] Custom user model with email login
- [x] Deck and card models with UUID keys
- [x] REST API with ownership enforcement and JWT auth
- [x] OpenAPI / Swagger documentation
- [x] Frontend — auth, deck list/create, card list/create ([#6](https://github.com/jakefred/WayOom-Bot/issues/6))
- [x] Test suite — 153 tests ([#9](https://github.com/jakefred/WayOom-Bot/issues/9))
- [x] CI pipeline — GitHub Actions ([#14](https://github.com/jakefred/WayOom-Bot/issues/14))
- [x] PostgreSQL support ([#5](https://github.com/jakefred/WayOom-Bot/issues/5))

### Done — Anki Parity

Card model expanded for lossless Anki import. See `docs/adding-model-fields.md` for the field-change checklist.

- [x] **Card types** — `basic`, `basic_reversed`, `cloze`
- [x] **Extra notes** — `extra_notes` JSON list for Anki's additional fields
- [x] **Spaced repetition** — `status`, `due_date`, `interval`, `ease_factor`, `review_count`, `lapse_count`
- [x] **Organization** — `flag` (0-7 color flags) and `position` (manual ordering)
- [x] **HTML rendering** — sanitized HTML via DOMPurify for `front`, `back`, and `extra_notes`
- [x] **`.apkg` import** — `POST /api/import/apkg/` + frontend upload UI. Supports `.anki2`, `.anki21`, and `.anki21b` (zstd-compressed) formats. Deterministic UUID v5 dedup, partial failure handling, 50 MB limit. 26 dedicated tests.

### Up Next

- [ ] **Media attachments** — `CardMedia` model for images/audio. Required for full `.apkg` fidelity.
- [ ] Flashcard study mode — flip cards front/back
- [ ] Edit and delete decks and cards from the UI
- [ ] Frontend design review ([#7](https://github.com/jakefred/WayOom-Bot/issues/7))
- [ ] Sidebar navigation ([#17](https://github.com/jakefred/WayOom-Bot/issues/17))
- [ ] Theme support ([#18](https://github.com/jakefred/WayOom-Bot/issues/18))
- [ ] WayOom icon ([#11](https://github.com/jakefred/WayOom-Bot/issues/11))
- [ ] Fix: anonymous users cannot read cards in public decks ([#1](https://github.com/jakefred/WayOom-Bot/issues/1))
- [ ] Documentation pass ([#8](https://github.com/jakefred/WayOom-Bot/issues/8))

### Before Production

- [ ] Rate limiting on auth endpoints ([#3](https://github.com/jakefred/WayOom-Bot/issues/3))
- [ ] Move refresh token to `httpOnly` cookie
- [ ] Password strength indicators ([#16](https://github.com/jakefred/WayOom-Bot/issues/16))
- [ ] Security review ([#10](https://github.com/jakefred/WayOom-Bot/issues/10))
- [ ] CD pipeline ([#19](https://github.com/jakefred/WayOom-Bot/issues/19))
- [ ] Account recovery and deletion ([#13](https://github.com/jakefred/WayOom-Bot/issues/13))

### Long Term

- Two-factor authentication ([#15](https://github.com/jakefred/WayOom-Bot/issues/15))
- Spaced repetition scheduling
- Rich card content (images, markdown, audio)
- Mobile-friendly experience
- Public deck sharing and discovery

---

## Built With

This project was built with the help of [Cursor](https://cursor.com/) and [Claude Code](https://claude.ai/claude-code).
