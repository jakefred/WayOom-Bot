# WayOom — Frontend

The web interface for WayOom, built with React 19, Vite, TypeScript, and [shadcn/ui](https://ui.shadcn.com/). Designed to feel clean and satisfying from day one, with room to grow into a full long-term memory experience.

For full project setup (backend, environment variables, running both servers), see the [root README](../README.md).

---

## Quick Start

```bash
npm install
npm run dev
```

The app runs at `http://localhost:5173`. Requests to `/api` are proxied to the Django backend at `http://127.0.0.1:8000` — both servers must be running for API calls to work.

---

## Project Structure

```
src/
├── api/
│   ├── auth.ts          # Typed fetch wrappers: register, login, refresh, logout
│   └── decks.ts         # Typed fetch wrappers: list/create decks and cards
├── components/
│   └── ui/              # shadcn/ui components (button, card, form, input, label)
├── context/
│   └── AuthContext.tsx   # JWT token state; provides useAuth() hook
├── lib/
│   ├── utils.ts         # cn() helper from shadcn/ui
│   └── sanitize.ts      # sanitizeCardHtml() — shared DOMPurify config
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── DeckListPage.tsx
│   ├── DeckDetailPage.tsx
│   └── StudyPage.tsx    # Flashcard study mode with progressive reveal
├── App.tsx              # BrowserRouter, AuthProvider, route definitions
└── main.tsx             # Entry point
```

---

## Routes

| Path             | Page              | Auth required |
|------------------|-------------------|---------------|
| `/login`         | LoginPage         | No            |
| `/register`      | RegisterPage      | No            |
| `/decks`         | DeckListPage      | Yes           |
| `/decks/:deckId` | DeckDetailPage    | Yes           |
| `/decks/:deckId/study` | StudyPage  | Yes           |
| `/`              | Redirects to `/decks` | —         |

Unauthenticated users are redirected to `/login`.

---

## Auth Pattern

Tokens are managed in `AuthContext`:

- **Access token** — held in React state (memory only). Sent as `Authorization: Bearer <token>` on every API request.
- **Refresh token** — stored in `localStorage` under `wayoom_refresh`. Survives page reloads.
- **Silent refresh** — on mount, `AuthContext` checks for a stored refresh token and calls `/api/auth/token/refresh/` to restore the session without requiring a new login.

> **Before production**, the refresh token will move to an `httpOnly` cookie to protect against XSS. Tracked in the [root README roadmap](../README.md#before-production).

---

## Making API Calls

Follow the pattern in `src/api/decks.ts`:

1. Get the access token from the auth context: `const { access } = useAuth()`
2. Pass it to the wrapper function: `apiListDecks(access)`
3. Wrap the call in `try/catch` — all wrappers throw a human-readable `Error` on non-2xx responses.

To add a new endpoint, add a typed function to the appropriate file in `src/api/` using the same `fetch` + `Authorization: Bearer` pattern.

---

## Adding shadcn/ui Components

Components live in `src/components/ui/`. To add a new one:

```bash
npx shadcn@latest add <component-name>
```

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `react-router-dom` | Client-side routing |
| `tailwindcss` + `@tailwindcss/vite` | Utility-first styling (v4) |
| `shadcn/ui` | Accessible component library |
| `react-hook-form` + `zod` | Form state and validation |
| `lucide-react` | Icon set |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
