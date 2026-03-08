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

export interface Card {
  id: string;
  deck: string;
  card_type: CardType;
  front: string;
  back: string;
  tags: string[];
  extra_notes: string[];
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
