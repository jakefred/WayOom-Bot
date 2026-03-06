/**
 * Typed fetch wrappers for all auth endpoints.
 *
 * All functions throw an Error with a human-readable message on non-2xx
 * responses so callers can surface the message directly in the UI.
 */

interface TokenPair {
  access: string;
  refresh: string;
}

/** Parse error detail from a DRF response body (best-effort). */
async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    // DRF typically sends { detail: "..." } or { field: ["msg"] }
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

export async function apiRegister(
  email: string,
  password: string,
  password2: string,
): Promise<TokenPair> {
  const res = await fetch("/api/auth/register/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, password2 }),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<TokenPair>;
}

export async function apiLogin(
  email: string,
  password: string,
): Promise<TokenPair> {
  const res = await fetch("/api/auth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<TokenPair>;
}

export async function apiRefresh(refresh: string): Promise<TokenPair> {
  const res = await fetch("/api/auth/token/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<TokenPair>;
}

export async function apiLogout(refresh: string): Promise<void> {
  const res = await fetch("/api/auth/logout/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
}
