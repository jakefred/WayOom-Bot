# Getting Started

## Backend

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

## Frontend

**Prerequisites:** Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. Requests to `/api` are proxied to the Django backend.

## API Documentation

Available when `DEBUG=True`:

| URL | Description |
|-----|-------------|
| `/api/schema/swagger-ui/` | Interactive Swagger UI |
| `/api/schema/redoc/` | ReDoc documentation |
| `/api/schema/` | Raw OpenAPI 3.0 schema |

See [`backend/README.md`](../backend/README.md) for full endpoint reference.
