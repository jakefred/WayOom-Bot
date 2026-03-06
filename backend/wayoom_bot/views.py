"""API views for Deck and Card resources.

Ownership enforcement strategy:
- get_queryset() scopes the initial queryset so users can only see objects they
  are allowed to read (own or public).
- IsOwnerOrReadOnly provides a second gate at the object level, blocking writes
  on objects the requesting user does not own.
- perform_create() injects server-controlled fields (user, deck) so clients can
  never self-assign ownership.
"""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Card, Deck
from .permissions import IsOwnerOrReadOnly
from .serializers import CardSerializer, DeckSerializer


class DeckViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for Deck objects.

    List / retrieve: returns decks the user owns plus all public decks.
    Create: assigns the deck to the requesting user automatically.
    Update / delete: restricted to the deck owner via IsOwnerOrReadOnly.
    """

    serializer_class = DeckSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Returns own decks + all public decks.
            return Deck.objects.visible_to(user)
        # Anonymous users may only browse public decks.
        return Deck.objects.filter(is_public=True)

    def perform_create(self, serializer):
        # Bind the deck to the logged-in user; the client cannot override this.
        serializer.save(user=self.request.user)


class CardViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for Card objects, always scoped to a parent Deck.

    The deck UUID comes from the URL (<deck_pk>), never from the request body.

    List / retrieve: returns cards in the given deck that are visible to the user.
    Create: verifies the requesting user owns the parent deck, then creates the card.
    Update / delete: restricted to the deck owner via IsOwnerOrReadOnly.
    """

    serializer_class = CardSerializer
    # Cards carry no public read path of their own — the deck's visibility
    # controls access — but IsAuthenticated keeps anonymous users out entirely
    # since card mutations require an account regardless.
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # select_related('deck') avoids a second DB hit when IsOwnerOrReadOnly
        # checks obj.deck.user for write operations.
        return (
            Card.objects.visible_to(self.request.user)
            .filter(deck_id=self.kwargs["deck_pk"])
            .select_related("deck")
        )

    def perform_create(self, serializer):
        # Fetch the parent deck, enforcing that the requesting user owns it.
        # owned_by() returns an empty queryset if ownership fails, so
        # get_object_or_404 would give a 404.  We raise PermissionDenied instead
        # so the client knows the deck exists but they don't own it.
        deck_pk = self.kwargs["deck_pk"]

        try:
            deck = Deck.objects.owned_by(self.request.user).get(pk=deck_pk)
        except Deck.DoesNotExist:
            # Return 403 rather than 404 to avoid leaking deck existence.
            raise PermissionDenied(
                "You do not have permission to add cards to this deck."
            )

        serializer.save(deck=deck)
