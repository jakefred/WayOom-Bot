# WayOom Bot Backend

Django REST API for managing flashcard decks and cards with spaced repetition support and Anki parity.

## Tech Stack

- **Django 6.0.3** + **Django REST Framework 3.16**
- **SimpleJWT** for token authentication (access + refresh with rotation and blacklisting)
- **drf-spectacular** for auto-generated OpenAPI 3.0 docs
- **python-dotenv** for auto-loading `.env` into the environment
- **PostgreSQL** (recommended) or **SQLite** (development fallback)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values (see Environment Variables below)
# .env is loaded automatically by settings.py via python-dotenv — no need to source it manually
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django secret key |
| `DEBUG` | No | `False` | Enable debug mode |
| `ALLOWED_HOSTS` | No | `[]` | Comma-separated hostnames |
| `DB_NAME` | No | — | PostgreSQL database name. If unset, uses SQLite |
| `DB_USER` | No | — | PostgreSQL user |
| `DB_PASSWORD` | No | — | PostgreSQL password |
| `DB_HOST` | No | `127.0.0.1` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## API Documentation

Interactive docs are available when the server is running:

- **Swagger UI:** `GET /api/schema/swagger-ui/`
- **ReDoc:** `GET /api/schema/redoc/`
- **Raw OpenAPI schema:** `GET /api/schema/`

## Authentication

All auth endpoints are under `/api/auth/`. The API uses JWT Bearer tokens.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | No | Create account |
| POST | `/api/auth/token/` | No | Login (obtain tokens) |
| POST | `/api/auth/token/refresh/` | No | Rotate refresh token |
| POST | `/api/auth/token/verify/` | No | Verify token validity |
| POST | `/api/auth/logout/` | Yes | Blacklist refresh token |

### Register

```
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "password2": "securepassword"
}
```

Response `201`:
```json
{
  "refresh": "eyJ...",
  "access": "eyJ..."
}
```

### Login

```
POST /api/auth/token/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

Response `200`:
```json
{
  "refresh": "eyJ...",
  "access": "eyJ..."
}
```

### Using Tokens

Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

- Access tokens expire in **15 minutes**
- Refresh tokens expire in **7 days**
- Refresh tokens **rotate** on each use (old ones are blacklisted)

## API Endpoints

### Decks

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/decks/` | Optional | List own decks + public decks |
| POST | `/api/decks/` | Required | Create a deck |
| GET | `/api/decks/<uuid>/` | Optional | Get a deck |
| PUT | `/api/decks/<uuid>/` | Required (owner) | Replace a deck |
| PATCH | `/api/decks/<uuid>/` | Required (owner) | Partially update a deck |
| DELETE | `/api/decks/<uuid>/` | Required (owner) | Delete a deck |

#### Deck Object

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Japanese Vocabulary",
  "user": 1,
  "description": "JLPT N5 vocabulary cards",
  "is_public": false,
  "created_at": "2026-03-09T12:00:00Z",
  "updated_at": "2026-03-09T12:00:00Z"
}
```

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | UUID | No | Auto-generated |
| `name` | string | Yes | Required, max 255 chars |
| `user` | integer | No | Set from authenticated user |
| `description` | string \| null | Yes | Optional, max 2,000 chars |
| `is_public` | boolean | Yes | Default `false` |
| `created_at` | datetime | No | Auto-set |
| `updated_at` | datetime | No | Auto-set |

### Cards

Cards are nested under their parent deck.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/decks/<deck_pk>/cards/` | Required | List cards in deck |
| POST | `/api/decks/<deck_pk>/cards/` | Required (deck owner) | Create a card |
| GET | `/api/decks/<deck_pk>/cards/<uuid>/` | Required | Get a card |
| PUT | `/api/decks/<deck_pk>/cards/<uuid>/` | Required (deck owner) | Replace a card |
| PATCH | `/api/decks/<deck_pk>/cards/<uuid>/` | Required (deck owner) | Partially update a card |
| DELETE | `/api/decks/<deck_pk>/cards/<uuid>/` | Required (deck owner) | Delete a card |

#### Card Object

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "deck": "550e8400-e29b-41d4-a716-446655440000",
  "card_type": "BASIC",
  "status": "NEW",
  "flag": 0,
  "position": null,
  "tags": ["vocabulary", "n5"],
  "front": "What does 猫 mean?",
  "back": "Cat",
  "extra_notes": [],
  "due_date": null,
  "interval": 0,
  "ease_factor": 2.5,
  "review_count": 0,
  "lapse_count": 0,
  "created_at": "2026-03-09T12:00:00Z",
  "updated_at": "2026-03-09T12:00:00Z"
}
```

| Field | Type | Writable | Notes |
|---|---|---|---|
| `id` | UUID | No | Auto-generated |
| `deck` | UUID | No | Set from URL |
| `card_type` | string | Yes | `BASIC`, `BASIC_REVERSED`, or `CLOZE`. Default `BASIC` |
| `status` | string | Yes | `NEW`, `LEARNING`, `REVIEW`, `SUSPENDED`, or `BURIED`. Default `NEW` |
| `flag` | integer | Yes | 0-7 color flag (0=none, 1=red, 2=orange, 3=green, 4=blue, 5=pink, 6=turquoise, 7=purple) |
| `position` | integer \| null | Yes | Manual ordering within deck |
| `tags` | string[] | Yes | Max 50 tags, each max 100 chars |
| `front` | string | Yes | Required, max 10,000 chars |
| `back` | string | Yes | Optional, max 10,000 chars |
| `extra_notes` | string[] | Yes | Max 20 items, each max 10,000 chars |
| `due_date` | datetime \| null | Yes | Next review date |
| `interval` | integer | Yes | Days until next review. Default 0 |
| `ease_factor` | float | Yes | Interval multiplier. Default 2.5 |
| `review_count` | integer | Yes | Total reviews completed. Default 0 |
| `lapse_count` | integer | Yes | Times forgotten. Default 0 |
| `created_at` | datetime | No | Auto-set |
| `updated_at` | datetime | No | Auto-set |

## Permissions Model

- **Unauthenticated users** can read public decks only (via `GET /api/decks/`)
- **Authenticated users** can read their own decks + public decks, and create new decks
- **Deck owners** have full CRUD on their decks and all cards within them
- Cards inherit visibility from their parent deck
- All IDs are UUIDs to prevent enumeration attacks
- Attempting to create a card in a non-owned deck returns `403 Forbidden`

## Data Model

```
User (email login)
 └── Deck (name, description, is_public)
      └── Card (front, back, card_type, tags, spaced repetition fields)
```

- Deleting a user cascades to all their decks and cards
- Deleting a deck cascades to all its cards
- Decks are private by default (`is_public=false`)

## Error Responses

Standard DRF error format:

```json
{"detail": "Authentication credentials were not provided."}
```

```json
{"field_name": ["This field is required."]}
```

| Status | Meaning |
|---|---|
| 400 | Validation error |
| 401 | Missing or invalid token |
| 403 | Not the resource owner |
| 404 | Resource not found (or not visible to you) |

## Project Structure

```
backend/
├── config/             # Django project settings and root URL config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── users/              # Authentication and user management
│   ├── models.py       # Custom User model (email-based login)
│   ├── views.py        # RegisterView
│   ├── serializers.py  # RegisterSerializer
│   ├── urls.py         # Auth routes
│   └── admin.py
├── wayoom_bot/         # Core flashcard functionality
│   ├── models.py       # Deck and Card models
│   ├── views.py        # DeckViewSet, CardViewSet
│   ├── serializers.py  # DeckSerializer, CardSerializer
│   ├── urls.py         # Deck and card routes
│   ├── permissions.py  # IsOwnerOrReadOnly
│   └── admin.py
├── manage.py
├── requirements.txt
├── .env.example
└── db.sqlite3          # Dev database (gitignored)
```
