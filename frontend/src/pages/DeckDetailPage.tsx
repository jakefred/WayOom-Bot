import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { apiListCards, apiCreateCard, type Card, type CardType } from "@/api/decks";
import {
  Card as UiCard,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function DeckDetailPage() {
  const { deckId } = useParams<{ deckId: string }>();
  const { access } = useAuth();

  const [cards, setCards] = useState<Card[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // New card form state
  const [cardType, setCardType] = useState<CardType>("basic");
  const [cardFront, setCardFront] = useState("");
  const [cardBack, setCardBack] = useState("");
  const [cardTagsRaw, setCardTagsRaw] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!access || !deckId) return;
    apiListCards(access, deckId)
      .then(setCards)
      .catch((err: unknown) =>
        setLoadError(err instanceof Error ? err.message : "Failed to load cards."),
      );
  }, [access, deckId]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!access || !deckId) return;
    setFormError(null);
    setSubmitting(true);

    // Parse comma-separated tags, stripping whitespace and empty values.
    const tags = cardTagsRaw
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      const newCard = await apiCreateCard(access, deckId, {
        card_type: cardType,
        front: cardFront,
        back: cardBack,
        tags,
      });
      setCards((prev) => [newCard, ...prev]);
      setCardType("basic");
      setCardFront("");
      setCardBack("");
      setCardTagsRaw("");
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create card.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/decks"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to Decks
            </Link>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? "Cancel" : "Add Card"}
          </Button>
        </div>

        {/* Add card form */}
        {showForm && (
          <UiCard className="mb-6">
            <CardHeader>
              <CardTitle>New flashcard</CardTitle>
            </CardHeader>
            <form onSubmit={handleCreate}>
              <CardContent className="space-y-4">
                {formError && (
                  <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {formError}
                  </p>
                )}
                <div className="space-y-1">
                  <Label htmlFor="card-type">Card type</Label>
                  <select
                    id="card-type"
                    value={cardType}
                    onChange={(e) => setCardType(e.target.value as CardType)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  >
                    <option value="basic">Basic</option>
                    <option value="basic_reversed">Basic (Reversed)</option>
                    <option value="cloze">Cloze</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="card-front">Front</Label>
                  <Input
                    id="card-front"
                    required
                    value={cardFront}
                    onChange={(e) => setCardFront(e.target.value)}
                    placeholder="The question or prompt shown first"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="card-back">Back</Label>
                  <Input
                    id="card-back"
                    required
                    value={cardBack}
                    onChange={(e) => setCardBack(e.target.value)}
                    placeholder="The answer revealed on flip"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="card-tags">Tags (optional, comma-separated)</Label>
                  <Input
                    id="card-tags"
                    value={cardTagsRaw}
                    onChange={(e) => setCardTagsRaw(e.target.value)}
                    placeholder="e.g. biology, chapter-3"
                  />
                </div>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Saving…" : "Save card"}
                </Button>
              </CardContent>
            </form>
          </UiCard>
        )}

        {/* Error loading cards */}
        {loadError && (
          <p className="mb-4 text-sm text-destructive">{loadError}</p>
        )}

        {/* Card list */}
        {cards.length === 0 && !loadError ? (
          <p className="text-center text-muted-foreground">
            No cards yet. Add your first one above.
          </p>
        ) : (
          <div className="space-y-4">
            {cards.map((card) => (
              <UiCard key={card.id}>
                <CardContent className="space-y-3 pt-6">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                      {card.card_type === "basic_reversed" ? "Basic (Reversed)" : card.card_type === "cloze" ? "Cloze" : "Basic"}
                    </span>
                    <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground capitalize">
                      {card.status}
                    </span>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Front
                    </p>
                    <p className="text-sm">{card.front}</p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Back
                    </p>
                    <p className="text-sm">{card.back}</p>
                  </div>
                  {card.extra_notes.length > 0 && (
                    <div className="space-y-2 border-t pt-3">
                      {card.extra_notes.map((note, i) => (
                        <p key={i} className="text-sm text-muted-foreground">
                          {note}
                        </p>
                      ))}
                    </div>
                  )}
                  {card.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {card.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </UiCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
