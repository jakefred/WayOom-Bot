import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { apiListDecks, apiCreateDeck, apiImportApkg, type Deck, type ApkgImportResult } from "@/api/decks";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function DeckListPage() {
  const { access, logout } = useAuth();
  const navigate = useNavigate();

  const [decks, setDecks] = useState<Deck[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // New deck form state
  const [deckName, setDeckName] = useState("");
  const [deckDesc, setDeckDesc] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Import state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ApkgImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  useEffect(() => {
    if (!access) return;
    apiListDecks(access)
      .then(setDecks)
      .catch((err: unknown) =>
        setLoadError(err instanceof Error ? err.message : "Failed to load decks."),
      );
  }, [access]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!access) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const newDeck = await apiCreateDeck(access, {
        name: deckName,
        description: deckDesc || undefined,
      });
      setDecks((prev) => [newDeck, ...prev]);
      setDeckName("");
      setDeckDesc("");
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create deck.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !access) return;
    // Reset so the same file can be re-selected after dismissing the result.
    e.target.value = "";
    setImportError(null);
    setImportResult(null);
    setImporting(true);
    try {
      const result = await apiImportApkg(access, file);
      setImportResult(result);
      // Refresh deck list so newly imported decks appear immediately.
      const updated = await apiListDecks(access);
      setDecks(updated);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background p-6">
      {/* Header */}
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold">My Decks</h1>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowForm((v) => !v)}
            >
              {showForm ? "Cancel" : "New Deck"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={importing}
              onClick={() => fileInputRef.current?.click()}
            >
              {importing ? "Importing…" : "Import .apkg"}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".apkg"
              className="hidden"
              onChange={handleImport}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void logout()}
            >
              Sign out
            </Button>
          </div>
        </div>

        {/* Import result banner */}
        {importResult && (
          <div className="mb-4 flex items-start justify-between rounded-md bg-green-500/10 px-4 py-3 text-sm text-green-700 dark:text-green-400">
            <div>
              <p className="font-medium">Import complete</p>
              <p>
                {importResult.decks_created} deck{importResult.decks_created !== 1 ? "s" : ""} created,{" "}
                {importResult.cards_created} card{importResult.cards_created !== 1 ? "s" : ""} imported
                {importResult.cards_skipped > 0 && `, ${importResult.cards_skipped} skipped (already exist)`}
              </p>
              {importResult.errors.length > 0 && (
                <ul className="mt-1 list-disc pl-4 text-yellow-700 dark:text-yellow-400">
                  {importResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
            </div>
            <button
              className="ml-4 text-lg leading-none opacity-60 hover:opacity-100"
              onClick={() => setImportResult(null)}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        {/* Import error banner */}
        {importError && (
          <div className="mb-4 flex items-start justify-between rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <p>{importError}</p>
            <button
              className="ml-4 text-lg leading-none opacity-60 hover:opacity-100"
              onClick={() => setImportError(null)}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        {/* New deck form */}
        {showForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Create a new deck</CardTitle>
            </CardHeader>
            <form onSubmit={handleCreate}>
              <CardContent className="space-y-4">
                {formError && (
                  <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {formError}
                  </p>
                )}
                <div className="space-y-1">
                  <Label htmlFor="deck-name">Name</Label>
                  <Input
                    id="deck-name"
                    required
                    value={deckName}
                    onChange={(e) => setDeckName(e.target.value)}
                    placeholder="e.g. Spanish Vocabulary"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="deck-desc">Description (optional)</Label>
                  <Input
                    id="deck-desc"
                    value={deckDesc}
                    onChange={(e) => setDeckDesc(e.target.value)}
                    placeholder="A short description of the deck"
                  />
                </div>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Creating…" : "Create deck"}
                </Button>
              </CardContent>
            </form>
          </Card>
        )}

        {/* Error loading decks */}
        {loadError && (
          <p className="mb-4 text-sm text-destructive">{loadError}</p>
        )}

        {/* Deck list */}
        {decks.length === 0 && !loadError ? (
          <p className="text-center text-muted-foreground">
            No decks yet. Create your first one above.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {decks.map((deck) => (
              <Card
                key={deck.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => navigate(`/decks/${deck.id}`)}
              >
                <CardHeader>
                  <CardTitle className="text-lg">{deck.name}</CardTitle>
                  {deck.description && (
                    <CardDescription className="line-clamp-2">
                      {deck.description}
                    </CardDescription>
                  )}
                </CardHeader>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
