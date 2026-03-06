import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import DeckListPage from "@/pages/DeckListPage";
import DeckDetailPage from "@/pages/DeckDetailPage";
import type { ReactNode } from "react";

/** Redirects unauthenticated users to /login; shows a loading screen while
 *  the context attempts a silent token refresh on mount. */
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { access, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  return access ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route
            path="/decks"
            element={
              <ProtectedRoute>
                <DeckListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/decks/:deckId"
            element={
              <ProtectedRoute>
                <DeckDetailPage />
              </ProtectedRoute>
            }
          />

          {/* Root redirects to the deck list */}
          <Route path="/" element={<Navigate to="/decks" replace />} />

          {/* Catch-all — redirect unknown paths to deck list */}
          <Route path="*" element={<Navigate to="/decks" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
