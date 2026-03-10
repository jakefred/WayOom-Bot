/**
 * Typed fetch wrappers for Deck and Card endpoints.
 *
 * Every function requires the JWT access token and sends it as
 * `Authorization: Bearer <token>`.  Non-2xx responses throw an Error
 * with a human-readable message suitable for displaying in the UI.
 */

export interface Deck {
  id: string;
  name: string;
  description: string | null;
  is_public: boolean;
  user: number;
  created_at: string;
  updated_at: string;
}

export type CardType = "basic" | "basic_reversed" | "cloze";
export type CardStatus = "new" | "learning" | "review" | "suspended" | "buried";

export interface Card {
  id: string;
  deck: string;
  card_type: CardType;
  status: CardStatus;
  flag: number;
  position: number | null;
  front: string;
  back: string;
  tags: string[];
  extra_notes: string[];
  due_date: string | null;
  interval: number;
  ease_factor: number;
  review_count: number;
  lapse_count: number;
  created_at: string;
  updated_at: string;
}

/** Parse error detail from a DRF response body (best-effort). */
async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    const firstField = Object.values(body)[0];
    if (Array.isArray(firstField) && typeof firstField[0] === "string") {
      return firstField[0];
    }
  } catch {
    // ignore parse errors
  }
  return `Request failed (${res.status})`;
}

export interface ApkgImportResult {
  decks_created: number;
  cards_created: number;
  cards_skipped: number;
  media_created: number;
  media_skipped: number;
  errors: string[];
}

function authHeaders(access: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${access}`,
  };
}

// --- Deck ---

export async function apiListDecks(access: string): Promise<Deck[]> {
  const res = await fetch("/api/decks/", {
    headers: authHeaders(access),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<Deck[]>;
}

export async function apiCreateDeck(
  access: string,
  data: { name: string; description?: string },
): Promise<Deck> {
  const res = await fetch("/api/decks/", {
    method: "POST",
    headers: authHeaders(access),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<Deck>;
}

// --- Import ---

export async function apiImportApkg(
  access: string,
  file: File,
): Promise<ApkgImportResult> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch("/api/import/apkg/", {
    method: "POST",
    headers: { Authorization: `Bearer ${access}` },
    body,
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<ApkgImportResult>;
}

// --- Card ---

export async function apiListCards(
  access: string,
  deckId: string,
): Promise<Card[]> {
  const res = await fetch(`/api/decks/${deckId}/cards/`, {
    headers: authHeaders(access),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<Card[]>;
}

export async function apiCreateCard(
  access: string,
  deckId: string,
  data: { front: string; back: string; card_type?: CardType; tags?: string[]; extra_notes?: string[] },
): Promise<Card> {
  const res = await fetch(`/api/decks/${deckId}/cards/`, {
    method: "POST",
    headers: authHeaders(access),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<Card>;
}
