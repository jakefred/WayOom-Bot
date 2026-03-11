import { useEffect, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { apiListCards, type Card } from "@/api/decks";
import { sanitizeCardHtml } from "@/lib/sanitize";
import { Button } from "@/components/ui/button";

export default function StudyPage() {
  const { deckId } = useParams<{ deckId: string }>();
  const { access } = useAuth();

  const [cards, setCards] = useState<Card[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [revealCount, setRevealCount] = useState(0);

  useEffect(() => {
    if (!access || !deckId) return;
    apiListCards(access, deckId)
      .then((fetched) => {
        setCards(fetched);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Failed to load cards.");
        setLoading(false);
      });
  }, [access, deckId]);

  const currentCard = cards[currentIndex] ?? null;

  // Number of fields that can be revealed after the front:
  // back counts as 1 (even if empty we skip it), plus each extra note.
  // We skip revealing the back if it's blank and there are no extra notes.
  const revealableFields: string[] = currentCard
    ? [
        ...(currentCard.back || currentCard.extra_notes.length > 0
          ? [currentCard.back]
          : []),
        ...currentCard.extra_notes,
      ]
    : [];

  const totalRevealable = revealableFields.length;
  const allRevealed = revealCount >= totalRevealable;
  const isComplete = currentIndex >= cards.length;

  const advance = useCallback(() => {
    if (!currentCard) return;
    if (totalRevealable === 0 || allRevealed) {
      // Move to the next card
      setCurrentIndex((i) => i + 1);
      setRevealCount(0);
    } else {
      setRevealCount((r) => r + 1);
    }
  }, [currentCard, totalRevealable, allRevealed]);

  const goBack = useCallback(() => {
    if (currentIndex === 0 && revealCount === 0) return;
    if (revealCount > 0) {
      setRevealCount((r) => r - 1);
    } else {
      setCurrentIndex((i) => i - 1);
      setRevealCount(0);
    }
  }, [currentIndex, revealCount]);

  // Keyboard support
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === " " || e.key === "Enter" || e.key === "ArrowRight") {
        e.preventDefault();
        advance();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        goBack();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance, goBack]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-sm text-destructive">{loadError}</p>
        <Button variant="outline" asChild>
          <Link to={`/decks/${deckId}`}>← Back to Deck</Link>
        </Button>
      </div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">No cards in this deck yet.</p>
        <Button variant="outline" asChild>
          <Link to={`/decks/${deckId}`}>← Back to Deck</Link>
        </Button>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-6">
        <div className="text-center">
          <p className="text-2xl font-semibold">All done!</p>
          <p className="mt-1 text-sm text-muted-foreground">
            You reviewed all {cards.length} card{cards.length !== 1 ? "s" : ""}.
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              setCurrentIndex(0);
              setRevealCount(0);
            }}
          >
            Study again
          </Button>
          <Button variant="outline" asChild>
            <Link to={`/decks/${deckId}`}>← Back to Deck</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4">
        <Link
          to={`/decks/${deckId}`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to Deck
        </Link>
        <span className="text-sm text-muted-foreground">
          {currentIndex + 1} / {cards.length}
        </span>
      </div>

      {/* Card area */}
      <div
        className="flex flex-1 cursor-pointer flex-col items-center justify-center px-6 pb-24"
        onClick={advance}
      >
        <div className="w-full max-w-2xl space-y-6">
          {/* Front — always visible */}
          <div className="rounded-xl border bg-card p-6 shadow-sm">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Front
            </p>
            <div
              className="text-base"
              dangerouslySetInnerHTML={{
                __html: sanitizeCardHtml(currentCard!.front),
              }}
            />
          </div>

          {/* Revealed fields */}
          {revealCount > 0 && (
            <div className="space-y-4">
              {revealableFields.slice(0, revealCount).map((field, i) => (
                <div
                  key={i}
                  className="rounded-xl border bg-card p-6 shadow-sm"
                >
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {i === 0 ? "Back" : `Note ${i}`}
                  </p>
                  <div
                    className="text-base"
                    dangerouslySetInnerHTML={{
                      __html: sanitizeCardHtml(field),
                    }}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Tap hint */}
          {!allRevealed && (
            <p className="text-center text-sm text-muted-foreground">
              {revealCount === 0 ? "Tap to reveal" : "Tap for next field"}
            </p>
          )}
          {allRevealed && (
            <p className="text-center text-sm text-muted-foreground">
              Tap to continue
            </p>
          )}
        </div>
      </div>

      {/* Dot indicators — fixed at the bottom */}
      {totalRevealable > 0 && (
        <div className="fixed bottom-8 left-0 right-0 flex justify-center gap-2">
          {revealableFields.map((_, i) => (
            <span
              key={i}
              className={`h-2 w-2 rounded-full transition-colors duration-200 ${
                i < revealCount
                  ? "bg-primary"
                  : "bg-muted-foreground/30"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
