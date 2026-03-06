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

   Django does not load `.env` by default — either set the variables in your shell or load them with `python-dotenv`.

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
- [x] Frontend scaffold (auth, deck list/create, card list/create)

### In Progress

- [ ] Flashcard study mode — flip cards front/back
- [ ] Edit and delete decks and cards from the UI
- [ ] Remove the name field from cards ([#12](https://github.com/jakefred/WayOom-Bot/issues/12))
- [ ] Account recovery and deletion ([#13](https://github.com/jakefred/WayOom-Bot/issues/13))
- [ ] Frontend design review ([#7](https://github.com/jakefred/WayOom-Bot/issues/7))

### Before Production

- [ ] Fix: anonymous users cannot read cards in public decks ([#1](https://github.com/jakefred/WayOom-Bot/issues/1))
- [ ] Switch from SQLite to PostgreSQL ([#5](https://github.com/jakefred/WayOom-Bot/issues/5))
- [ ] Rate limiting on auth endpoints ([#3](https://github.com/jakefred/WayOom-Bot/issues/3))
- [ ] Move refresh token from `localStorage` to an `httpOnly` cookie
- [ ] Security review ([#10](https://github.com/jakefred/WayOom-Bot/issues/10))
- [ ] Testing ([#9](https://github.com/jakefred/WayOom-Bot/issues/9))
- [ ] CI/CD pipeline ([#14](https://github.com/jakefred/WayOom-Bot/issues/14))
- [ ] Documentation pass ([#8](https://github.com/jakefred/WayOom-Bot/issues/8))

### Long Term

- Spaced repetition scheduling
- Rich card content (images, markdown, audio)
- Mobile-friendly experience
- Public deck sharing and discovery

---

## Built With

This project was built with the help of [Cursor](https://cursor.com/) and [Claude Code](https://claude.ai/claude-code).
