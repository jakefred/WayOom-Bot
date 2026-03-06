# WayOom Bot — Frontend

React 19 + Vite + TypeScript flashcard frontend.

For full project setup (backend, environment variables, running both servers), see the [root README](../README.md).

---

## Quick start

```bash
npm install
npm run dev
```

The app runs at `http://localhost:5173`. Requests to `/api` are proxied to the Django backend at `http://127.0.0.1:8000` — both servers must be running for API calls to work.

---

## Project structure

```
src/
├── api/
│   ├── auth.ts      # Typed fetch wrappers: register, login, refresh, logout
│   └── decks.ts     # Typed fetch wrappers: list/create decks and cards
├── components/
│   └── ui/          # shadcn/ui components (button, card, form, input, label)
├── context/
│   └── AuthContext.tsx  # JWT token state; provides useAuth() hook
├── lib/
│   └── utils.ts     # cn() helper from shadcn/ui
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── DeckListPage.tsx
│   └── DeckDetailPage.tsx
├── App.tsx          # BrowserRouter, AuthProvider, route definitions
└── main.tsx         # Entry point
```

---

## Routes

| Path             | Page              | Auth required |
|------------------|-------------------|---------------|
| `/login`         | LoginPage         | No            |
| `/register`      | RegisterPage      | No            |
| `/decks`         | DeckListPage      | Yes           |
| `/decks/:deckId` | DeckDetailPage    | Yes           |
| `/`              | Redirects to `/decks` | —         |

Unauthenticated users trying to reach a protected route are redirected to `/login`.

---

## Auth pattern

Tokens are managed in `AuthContext`:

- **Access token** — stored in React state (memory only). Sent as `Authorization: Bearer <token>` on every API request.
- **Refresh token** — stored in `localStorage` under the key `wayoom_refresh`. Survives page reloads.
- **Silent refresh** — on mount, `AuthContext` checks `localStorage` for a refresh token and calls `/api/auth/token/refresh/` to restore the session without requiring the user to log in again.

> Before going to production, the refresh token should be moved to an `httpOnly` cookie (tracked in GitHub issue #3).

---

## Making API calls

Follow the pattern in `src/api/decks.ts`:

1. Get the access token from the auth context: `const { access } = useAuth()`
2. Pass it to the relevant wrapper function: `apiListDecks(access)`
3. Wrap the call in a `try/catch` — all wrappers throw a human-readable `Error` on non-2xx responses.

To add a new endpoint, add a typed function to the appropriate file in `src/api/` using the same `fetch` + `Authorization: Bearer` pattern.

---

## Adding shadcn/ui components

Components live in `src/components/ui/`. To add a new one:

```bash
npx shadcn@latest add <component-name>
```

---

## Key dependencies

| Package | Purpose |
|---------|---------|
| `react-router-dom` | Client-side routing |
| `tailwindcss` + `@tailwindcss/vite` | Utility-first styling (v4) |
| `shadcn/ui` | Pre-built accessible component library |
| `react-hook-form` + `zod` | Form state and validation (installed by shadcn) |
| `lucide-react` | Icon set (installed by shadcn) |

## Available scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
