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
├── backend/             # Django REST API (config, users, wayoom_bot apps)
├── frontend/            # Vite + React + TypeScript + shadcn/ui
└── docs/                # Architecture and development guides
```

See [`docs/project_structure.md`](docs/project_structure.md) for the full file tree with annotations.

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

See [`docs/roadmap.md`](docs/roadmap.md).

---

## Built With

This project was built with the help of [Cursor](https://cursor.com/) and [Claude Code](https://claude.ai/claude-code).
