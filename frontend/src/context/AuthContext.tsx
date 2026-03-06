/**
 * AuthContext — provides auth state and actions to the entire component tree.
 *
 * Token strategy:
 *   access token  → stored in React state (memory only, cleared on tab close)
 *   refresh token → stored in localStorage (survives page refresh)
 *
 * On mount the context attempts a silent token refresh so the user stays
 * logged in after a page reload without having to re-enter credentials.
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { apiLogin, apiLogout, apiRefresh, apiRegister } from "@/api/auth";

const REFRESH_KEY = "wayoom_refresh";

interface AuthContextValue {
  /** JWT access token, or null when logged out. */
  access: string | null;
  /** True while the initial silent-refresh attempt is in progress. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, password2: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [access, setAccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Attempt silent refresh on initial mount so the user stays logged in
  // across page reloads (as long as a valid refresh token is in localStorage).
  useEffect(() => {
    const stored = localStorage.getItem(REFRESH_KEY);
    if (!stored) {
      // No token to refresh — mark loading complete without a state update
      // inside the effect body (React will batch this with the initial render).
      queueMicrotask(() => setLoading(false));
      return;
    }
    apiRefresh(stored)
      .then(({ access: newAccess, refresh: newRefresh }) => {
        setAccess(newAccess);
        localStorage.setItem(REFRESH_KEY, newRefresh);
      })
      .catch(() => {
        // Refresh token is expired or invalid — clear it.
        localStorage.removeItem(REFRESH_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access: newAccess, refresh: newRefresh } = await apiLogin(email, password);
    setAccess(newAccess);
    localStorage.setItem(REFRESH_KEY, newRefresh);
  }, []);

  const register = useCallback(
    async (email: string, password: string, password2: string) => {
      const { access: newAccess, refresh: newRefresh } = await apiRegister(
        email,
        password,
        password2,
      );
      setAccess(newAccess);
      localStorage.setItem(REFRESH_KEY, newRefresh);
    },
    [],
  );

  const logout = useCallback(async () => {
    const stored = localStorage.getItem(REFRESH_KEY);
    if (stored) {
      try {
        await apiLogout(stored);
      } catch {
        // Best-effort — clear local state regardless of server response.
      }
    }
    setAccess(null);
    localStorage.removeItem(REFRESH_KEY);
  }, []);

  return (
    <AuthContext.Provider value={{ access, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Convenience hook — throws if used outside of <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
