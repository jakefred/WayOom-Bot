# Project Structure

```
WayOom Bot/
├── backend/                        Django REST API
│   ├── config/                     Project settings and root URL config
│   │   ├── settings.py             Django settings (DB, JWT, DRF, OpenAPI)
│   │   ├── urls.py                 Mounts /admin/, /api/auth/, /api/, /api/schema/
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── users/                      Authentication and user management
│   │   ├── models.py               Custom User model — email as login, no username
│   │   ├── views.py                RegisterView (returns JWT pair on signup)
│   │   ├── serializers.py          RegisterSerializer — validates email, passwords
│   │   ├── urls.py                 /api/auth/* routes (register, token, refresh, verify, logout)
│   │   └── admin.py
│   ├── wayoom_bot/                 Core flashcard functionality
│   │   ├── models.py               Deck, Card, DeckMedia + ownership-scoped querysets
│   │   ├── views.py                DeckViewSet, CardViewSet, ApkgImportView, DeckMediaView
│   │   ├── serializers.py          DeckSerializer, CardSerializer, ApkgImportSerializer + media URL rewriting
│   │   ├── urls.py                 Deck, card, media, and import routes
│   │   ├── permissions.py          IsOwnerOrReadOnly — blocks writes on non-owned objects
│   │   ├── admin.py                Admin config with inline editors for cards and media
│   │   ├── importers/
│   │   │   └── apkg.py             .apkg parser — schema v11 + v18, zstd, protobuf, media extraction
│   │   ├── test_fixtures/
│   │   │   ├── build_fixtures.py   Script to regenerate .apkg test fixtures
│   │   │   ├── basic_deck.apkg     One deck, two cards, tags, SR fields
│   │   │   ├── multi_deck.apkg     Two nested decks (Languages::Python, Languages::Java)
│   │   │   └── card_types.apkg     Basic, basic_reversed, and cloze card types
│   │   ├── tests.py                166 tests — models, views, import, media, serializers
│   │   └── migrations/             0001 through 0009
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   └── media/                      Uploaded files from .apkg imports (gitignored)
│
├── frontend/                       Vite + React 19 + TypeScript + shadcn/ui
│   ├── src/
│   │   ├── api/
│   │   │   ├── auth.ts             Typed fetch wrappers: register, login, refresh, logout
│   │   │   └── decks.ts            Typed fetch wrappers: decks, cards, .apkg import
│   │   ├── components/
│   │   │   └── ui/                 shadcn/ui primitives (button, card, form, input, label)
│   │   ├── context/
│   │   │   └── AuthContext.tsx      JWT state — access in memory, refresh in localStorage, silent refresh on mount
│   │   ├── lib/
│   │   │   └── utils.ts            cn() helper from shadcn/ui
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── DeckListPage.tsx    Deck list, new deck form, .apkg import button
│   │   │   └── DeckDetailPage.tsx  Card list with sanitized HTML rendering (DOMPurify)
│   │   ├── App.tsx                 BrowserRouter, AuthProvider, route definitions, ProtectedRoute
│   │   └── main.tsx                Entry point
│   ├── index.html
│   ├── vite.config.ts              Proxy /api → http://127.0.0.1:8000
│   ├── package.json
│   └── components.json             shadcn/ui configuration
│
├── docs/
│   ├── adding-model-fields.md      Checklist for extending the Card model
│   └── project_structure.md        This file
│
├── .github/
│   └── workflows/                  CI pipeline — runs tests and lint on push/PR
│
├── .gitignore
└── README.md
```

---

## Backend — Django apps

### `config/` — Project settings

[settings.py](../backend/config/settings.py) handles:

- **Database**: PostgreSQL if `DB_NAME` is set, otherwise SQLite fallback.
- **JWT auth**: 15-minute access tokens, 7-day rotating refresh tokens with blacklisting.
- **OpenAPI**: drf-spectacular generates schema; Swagger UI and ReDoc served at `/api/schema/`.
- **Media storage**: `MEDIA_ROOT = backend/media/`. Files served through an authenticated API view, not Django's default media handler.
- **Environment**: All secrets loaded from `.env` via `python-dotenv`.

[urls.py](../backend/config/urls.py) mounts:

| Prefix | App | Purpose |
|---|---|---|
| `/admin/` | Django admin | Built-in admin interface |
| `/api/auth/` | `users.urls` | Registration, JWT token lifecycle, logout |
| `/api/` | `wayoom_bot.urls` | Decks, cards, media, import |
| `/api/schema/` | drf-spectacular | OpenAPI schema, Swagger UI, ReDoc |

### `users/` — Authentication

Custom `User` model that uses **email as the login identifier** — no username field. Built on `AbstractUser` + custom `UserManager`.

[views.py](../backend/users/views.py): `RegisterView` creates the user and immediately returns a `{access, refresh}` token pair. All other auth endpoints (login, refresh, verify, logout) are provided by SimpleJWT.

### `wayoom_bot/` — Core app

#### Models ([models.py](../backend/wayoom_bot/models.py))

| Model | Key fields | Notes |
|---|---|---|
| `Deck` | `id` (UUID), `name`, `user` (FK), `is_public`, `description` | Owned by one user. Private by default. |
| `Card` | `id` (UUID), `deck` (FK), `front`, `back`, `extra_notes`, `card_type`, `tags`, SR fields | Inherits deck's privacy. Supports basic/reversed/cloze types. |
| `DeckMedia` | `id` (UUID), `deck` (FK), `original_filename`, `file`, `content_type`, `file_size` | Unique on `(deck, original_filename)`. MIME type auto-detected. |

Each model has a custom **QuerySet** (`DeckQuerySet`, `CardQuerySet`, `DeckMediaQuerySet`) with:
- `visible_to(user)` — own objects + public objects (used for reads)
- `owned_by(user)` — own objects only (used for writes)

Views always go through these methods — never raw, unscoped queries.

#### Views ([views.py](../backend/wayoom_bot/views.py))

| View | Endpoint | Purpose |
|---|---|---|
| `DeckViewSet` | `/api/decks/` | CRUD for decks. List returns own + public. |
| `CardViewSet` | `/api/decks/<id>/cards/` | CRUD for cards, scoped to parent deck. |
| `ApkgImportView` | `POST /api/import/apkg/` | Parses .apkg, creates decks/cards/media in a transaction. |
| `DeckMediaView` | `GET /api/decks/<id>/media/<filename>` | Serves media files with ownership enforcement. |

#### Serializers ([serializers.py](../backend/wayoom_bot/serializers.py))

`CardSerializer.to_representation()` rewrites bare media references in card HTML at API time:
- `<img src="cat.jpg">` becomes `<img src="/api/decks/{id}/media/cat.jpg">`
- `[sound:file.mp3]` becomes `<audio controls src="/api/decks/{id}/media/file.mp3"></audio>`

This keeps the raw Anki HTML clean in the database and avoids baking in URL schemes.

#### Importers ([importers/apkg.py](../backend/wayoom_bot/importers/apkg.py))

`parse_apkg(file_bytes)` → `ParseResult(decks, cards, media, errors)`

Supports all three Anki archive formats:
- `.anki2` — schema v11, plain SQLite
- `.anki21` — schema v11, plain SQLite
- `.anki21b` — schema v18, zstd-compressed SQLite, Protobuf template configs

Uses **deterministic UUID v5** for deduplication — re-importing the same file silently skips existing cards and media.

#### Permissions ([permissions.py](../backend/wayoom_bot/permissions.py))

`IsOwnerOrReadOnly` — DRF permission class that:
- Allows read access (GET, HEAD, OPTIONS) for any visible object
- Restricts write access (POST, PUT, PATCH, DELETE) to the object's owner
- Works for both `Deck` (via `obj.user`) and `Card` (via `obj.deck.user`)

---

## Frontend — React app

### Auth flow ([AuthContext.tsx](../frontend/src/context/AuthContext.tsx))

- **Access token** — held in React state (memory only). Sent as `Authorization: Bearer <token>`.
- **Refresh token** — stored in `localStorage`. Survives page reloads.
- **Silent refresh** — on mount, checks for a stored refresh token and calls `/api/auth/token/refresh/` to restore the session.
- Methods: `login()`, `register()`, `logout()` — all update tokens in state and `localStorage`.

### Routing ([App.tsx](../frontend/src/App.tsx))

| Path | Page | Auth |
|---|---|---|
| `/login` | LoginPage | No |
| `/register` | RegisterPage | No |
| `/decks` | DeckListPage | Yes |
| `/decks/:deckId` | DeckDetailPage | Yes |
| `/` | Redirects to `/decks` | — |

`ProtectedRoute` redirects unauthenticated users to `/login` and shows a loading screen during silent token refresh.

### API layer ([src/api/](../frontend/src/api/))

All API calls are typed `fetch` wrappers that:
1. Accept the JWT access token as a parameter
2. Send `Authorization: Bearer <token>`
3. Throw a human-readable `Error` on non-2xx responses

### Card HTML rendering

Card fields (`front`, `back`, `extra_notes`) contain HTML from Anki imports. The backend rewrites media URLs at API time; the frontend sanitizes the HTML via **DOMPurify** with `<audio>` and `controls` added to the allow list.

---

## Key dependencies

### Backend

| Package | Purpose |
|---|---|
| Django 6.0 | Web framework |
| djangorestframework | REST API toolkit |
| djangorestframework-simplejwt | JWT authentication with token rotation + blacklisting |
| drf-spectacular | Auto-generated OpenAPI 3.0 schema |
| psycopg2-binary | PostgreSQL adapter |
| python-dotenv | Auto-load `.env` into environment |
| zstandard | Decompress `.anki21b` archives |

### Frontend

| Package | Purpose |
|---|---|
| React 19 | UI library |
| Vite | Build tool with HMR |
| TypeScript | Type safety |
| Tailwind CSS v4 | Utility-first styling |
| shadcn/ui | Accessible component library |
| react-router-dom | Client-side routing |
| react-hook-form + zod | Form state and validation |
| dompurify | HTML sanitization for card content |
| lucide-react | Icon set |
