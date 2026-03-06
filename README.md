# WayOom Bot

> Work in progress — this document will be expanded as the project grows.

A flashcard app with a Django + DRF backend and a React (Vite + TypeScript) frontend.

---

## Project Structure

```
WayOom Bot/
├── backend/
│   ├── config/          # Django project settings, URLs, WSGI/ASGI
│   ├── users/           # Custom user model (email-based login)
│   ├── wayoom_bot/      # Main application (models, views, serializers, admin)
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Vite + React + TypeScript + shadcn/ui; dev server proxies /api to Django
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.12+

### Setup

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

   Open `backend/.env` and fill in the values. Django does not load `.env` by default, so when you run `manage.py` (migrate, runserver, etc.) you must either set `SECRET_KEY` (and optionally `DEBUG`, `ALLOWED_HOSTS`) in your shell from the values in `backend/.env`, or load `.env` yourself (e.g. with `python-dotenv` in settings). To generate a `SECRET_KEY`:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. **Run migrations**

   ```bash
   cd backend
   python manage.py migrate
   ```

6. **Create a superuser** (for Django admin access)

   ```bash
   python manage.py createsuperuser
   ```

   The prompt asks for **email** (not username) and password, because the project uses a custom user model with email as the login identifier.

7. **Start the development server**

   ```bash
   python manage.py runserver
   ```

   The API will be available at `http://127.0.0.1:8000/` and the admin at `http://127.0.0.1:8000/admin/`.

   **API docs** (only available while `DEBUG=True`):
   | URL | Description |
   |-----|-------------|
   | `http://127.0.0.1:8000/api/schema/` | Raw OpenAPI 3.0 schema (YAML/JSON) |
   | `http://127.0.0.1:8000/api/schema/swagger-ui/` | Interactive Swagger UI |
   | `http://127.0.0.1:8000/api/schema/redoc/` | ReDoc documentation |

### Frontend

- **Prerequisite:** Node.js (e.g. 18+).

- From the project root:

  ```bash
  cd frontend
  npm install
  npm run dev
  ```

  The app runs at `http://localhost:5173`. Requests to `/api` are proxied to the Django backend at `http://127.0.0.1:8000`, so run both the backend and frontend dev servers when working on features that call the API.

  See [`frontend/README.md`](frontend/README.md) for frontend-specific details (project structure, routes, auth pattern, adding new API calls).

---

## Architecture

The backend is a standard Django + DRF layered architecture:

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
  Database
```

### Key design decisions

- **Custom User model** (`users.User`) with **email as the login identifier** (no username required). `createsuperuser` and the admin use email.
- **UUID primary keys** on all models to prevent ID enumeration attacks.
- **`DeckQuerySet`** centralizes access control. Views must use `Deck.objects.visible_to(user)` for reads and `Deck.objects.owned_by(user)` for writes — never unscoped queries.
- **Cards inherit their deck's privacy.** A card should be treated as private if its parent deck is private.
- **Secrets are read from environment variables**, never hardcoded. See `backend/.env.example`.

---

## Roadmap

- [x] Frontend (scaffold in place)
- [x] Serializers for Deck and Card
- [x] REST API views with ownership enforcement
- [x] JWT authentication
- [x] API documentation (OpenAPI / Swagger)
- [x] Connect frontend to API (auth + deck list/create + card list/create)

**Up next:**

- [ ] Flashcard study mode (flip cards front/back)
- [ ] Edit and delete decks and cards from the UI
- [ ] Fix: anonymous users cannot read cards in public decks (GitHub issue #1)
- [ ] Switch from SQLite to PostgreSQL before production (GitHub issue #4)
- [ ] Rate limiting on auth endpoints (GitHub issue #3)
- [ ] Move refresh token from `localStorage` to an `httpOnly` cookie
