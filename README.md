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
│   ├── wayoom_bot/      # Core app — models, views, serializers, admin
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Vite + React + TypeScript + shadcn/ui
└── README.md
```

---

## Getting Started

### Backend

**Prerequisites:** Python 3.12+

1. **Clone the repository**

   ```bash
   git clone https://github.com/jakefred/WayOom-Bot.git
   cd "WayOom Bot"
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv backend/.venv

   # Windows
   backend\.venv\Scripts\activate

   # macOS / Linux
   source backend/.venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp backend/.env.example backend/.env
   ```

   Open `backend/.env` and fill in the values. To generate a `SECRET_KEY`:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   **PostgreSQL:** To use PostgreSQL instead of SQLite, set `DB_NAME`, `DB_USER`, and `DB_PASSWORD` (and optionally `DB_HOST`, `DB_PORT`) in `.env`. Create the database first: `createdb wayoom` (or via psql/pgAdmin). If `DB_NAME` is not set, the app falls back to SQLite.

   `.env` is loaded automatically by `settings.py` via `python-dotenv` — no need to source it manually.

5. **Run migrations and start the server**

   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

   The API is at `http://127.0.0.1:8000/` and the admin at `http://127.0.0.1:8000/admin/`.

6. **Create a superuser** (optional, for admin access)

   ```bash
   python manage.py createsuperuser
   ```

   The prompt asks for **email** and password — no username, by design.

### Frontend

**Prerequisites:** Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`. Requests to `/api` are proxied to the Django backend, so both servers need to be running.

See [`frontend/README.md`](frontend/README.md) for frontend-specific details.

### API Documentation

Available when `DEBUG=True`:

| URL | Description |
|-----|-------------|
| `/api/schema/` | Raw OpenAPI 3.0 schema |
| `/api/schema/swagger-ui/` | Interactive Swagger UI |
| `/api/schema/redoc/` | ReDoc documentation |

---

## Architecture

```
Client Request
      │
      ▼
   Views          Handle HTTP, enforce authentication, call queryset methods
      │
      ▼
 Serializers      Validate input, convert between JSON and Python objects
      │
      ▼
 QuerySets        Ownership-scoped database queries (visible_to / owned_by)
      │
      ▼
   Models         Database schema and data validation
      │
      ▼
  Database        SQLite in development, PostgreSQL in production
```

### Key Design Decisions

- **Email-based authentication.** The custom user model (`users.User`) uses email as the login identifier. No username field.
- **UUID primary keys** on all models to prevent ID enumeration.
- **Ownership-scoped queries.** `DeckQuerySet` centralizes access control. Views use `visible_to(user)` for reads and `owned_by(user)` for writes — never raw, unscoped queries.
- **Cards inherit deck privacy.** A card is only as public as its parent deck.
- **Secrets stay out of code.** All sensitive values are read from environment variables.

---

## Roadmap

### Done

- [x] Custom user model with email login
- [x] Deck and card models with UUID keys
- [x] REST API with ownership enforcement
- [x] JWT authentication
- [x] OpenAPI / Swagger documentation
- [x] Frontend scaffold — auth, deck list/create, card list/create ([#6](https://github.com/jakefred/WayOom-Bot/issues/6))
- [x] Model and view test suite — 127 tests ([#9](https://github.com/jakefred/WayOom-Bot/issues/9))
- [x] CI pipeline — GitHub Actions runs tests and lint on every push/PR ([#14](https://github.com/jakefred/WayOom-Bot/issues/14))
- [x] Remove the name field from cards ([#12](https://github.com/jakefred/WayOom-Bot/issues/12))

### In Progress — Anki Parity

Expanding the Card model so importing from Anki is lossless and users don't feel like they downgraded. See `docs/adding-model-fields.md` for the field-change checklist.

- [x] **Card type** — `card_type` field: `basic`, `basic_reversed`, `cloze`. Determines how the card is studied and maps to Anki's note types.
- [x] **Extra field** — `extra_notes` JSON list mapping to Anki's `flds[2+]` — ordered additional fields for context, hints, and supplementary answers.
- [x] **Spaced repetition fields** — `status` (new/learning/review/suspended/buried), `due_date`, `interval`, `ease_factor`, `review_count`, `lapse_count`. Stores scheduling state so imported Anki data is preserved and WayOom can run its own SR algorithm later.
- [x] **Organization fields** — `flag` (0–7 color flags, matches Anki) and `position` (manual ordering within a deck).
- [ ] **HTML rendering** — Anki fields contain HTML. Render `front`, `back`, and `extra` as sanitized HTML in the frontend (DOMPurify) instead of plain text.
- [ ] **Anki `.apkg` import** — `POST /api/import/apkg/` endpoint + frontend upload UI. Converts Anki decks and notes into WayOom Decks and Cards. Supports all three `.apkg` format versions including zstd-compressed `.anki21b`.
- [ ] **Media attachments** — `CardMedia` model linking files (images, audio) to cards. Required for full `.apkg` import fidelity.

### Housekeeping

- [x] Commit the PostgreSQL switch (`settings.py` + `requirements.txt` + `python-dotenv`)
- [x] Quote `DB_PASSWORD` in `backend/.env` to handle special characters
- [x] Run `pip install -r backend/requirements.txt` to install `psycopg2-binary` and `python-dotenv` in the venv
- [x] Add `*.code-workspace` to `.gitignore`
- [x] Move `tmp_issue_body.md` to `docs/apkg-import-spec.md` or add to `.gitignore`
- [x] Commit the `tags` fix in `CardAdmin.search_fields` (accidentally dropped during extra_notes step)

### Short Term — Core Experience

- [ ] Flashcard study mode — flip cards front/back
- [ ] Edit and delete decks and cards from the UI
- [ ] Frontend design review ([#7](https://github.com/jakefred/WayOom-Bot/issues/7))
- [ ] Add a sidebar to the UI ([#17](https://github.com/jakefred/WayOom-Bot/issues/17))
- [ ] Add a theme ([#18](https://github.com/jakefred/WayOom-Bot/issues/18))
- [ ] WayOom icon ([#11](https://github.com/jakefred/WayOom-Bot/issues/11))
- [ ] Fix: anonymous users cannot read cards in public decks ([#1](https://github.com/jakefred/WayOom-Bot/issues/1))
- [ ] Tag validation comment — document intentional duplication ([#2](https://github.com/jakefred/WayOom-Bot/issues/2))
- [ ] Documentation pass ([#8](https://github.com/jakefred/WayOom-Bot/issues/8))

### Before Production — Security & Infrastructure

- [ ] Rate limiting on auth endpoints ([#3](https://github.com/jakefred/WayOom-Bot/issues/3))
- [ ] Move refresh token from `localStorage` to an `httpOnly` cookie
- [ ] Add password strength indicators to the UI ([#16](https://github.com/jakefred/WayOom-Bot/issues/16))
- [ ] Security review ([#10](https://github.com/jakefred/WayOom-Bot/issues/10))
- [x] Switch from SQLite to PostgreSQL ([#5](https://github.com/jakefred/WayOom-Bot/issues/5))
- [ ] CD pipeline — automated deployment ([#19](https://github.com/jakefred/WayOom-Bot/issues/19))
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
