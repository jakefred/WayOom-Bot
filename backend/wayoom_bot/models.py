"""Models for decks and cards used by the WayOom bot."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
import uuid


MAX_TAGS_PER_CARD = 50
MAX_TAG_LENGTH = 100


def validate_tag_list(value):
    """Ensure tags is a flat list of non-empty strings.

    Limits:
    - At most MAX_TAGS_PER_CARD (50) tags per card.
    - Each tag must be a non-empty string of at most MAX_TAG_LENGTH (100) chars.

    These limits are enforced at the model layer so they apply everywhere data
    is saved, not just through the API serializer.
    """
    if not isinstance(value, list):
        raise ValidationError("Tags must be a list.")
    if len(value) > MAX_TAGS_PER_CARD:
        raise ValidationError(
            f"A card can have at most {MAX_TAGS_PER_CARD} tags. "
            f"Got {len(value)}."
        )
    for tag in value:
        if not isinstance(tag, str) or not tag.strip():
            raise ValidationError(
                "Each tag must be a non-empty string. "
                f"Got invalid value: {tag!r}"
            )
        if len(tag) > MAX_TAG_LENGTH:
            raise ValidationError(
                f"Each tag must be at most {MAX_TAG_LENGTH} characters. "
                f"Got tag of length {len(tag)}."
            )


class DeckQuerySet(models.QuerySet):
    """Ownership-aware queryset for Deck.

    Always use these methods in views instead of unscoped queries to avoid
    accidentally exposing private decks (IDOR vulnerabilities).
    """

    def visible_to(self, user):
        """Return decks owned by the user or marked public."""
        return self.filter(
            models.Q(user=user) | models.Q(is_public=True)
        )

    def owned_by(self, user):
        """Return only decks owned by the user (use for write operations)."""
        return self.filter(user=user)


class Deck(models.Model):
    """A collection of flashcards owned by a user.

    Use Deck.objects.visible_to(user) for reads and owned_by(user) for writes.
    """

    # UUID prevents ID enumeration — attackers cannot guess another user's deck ID.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decks",
    )
    description = models.TextField(
        blank=True,
        null=True,
        validators=[MaxLengthValidator(2_000)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)  # private by default; must be explicitly published

    objects = DeckQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Speeds up "list decks owned by this user, newest first" — the primary dashboard query.
            models.Index(fields=["user", "-created_at"], name="wayoom_deck_user_created_idx"),
            # Speeds up browsing the public deck gallery.
            models.Index(fields=["is_public", "-created_at"], name="wayoom_deck_public_created_idx"),
        ]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Deck id={self.id} name={self.name!r} user_id={self.user_id}>"


class CardQuerySet(models.QuerySet):
    """Ownership-aware queryset for Card.

    Always use these methods in views instead of unscoped queries to avoid
    exposing cards from other users' private decks (IDOR vulnerabilities).
    A card's visibility is determined entirely by its parent deck.
    """

    def visible_to(self, user):
        """Return cards whose deck is owned by the user or marked public."""
        return self.filter(
            models.Q(deck__user=user) | models.Q(deck__is_public=True)
        )

    def owned_by(self, user):
        """Return only cards whose deck is owned by the user (use for write operations)."""
        return self.filter(deck__user=user)


class Card(models.Model):
    """An individual flashcard belonging to a deck.

    Cards inherit their deck's privacy — treat a card as private if its deck is.
    Use Card.objects.visible_to(user) for reads and owned_by(user) for writes.
    """

    # UUID prevents ID enumeration (same reasoning as Deck).
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="cards")
    tags = models.JSONField(default=list, validators=[validate_tag_list])
    front = models.TextField(validators=[MaxLengthValidator(10_000)])
    back = models.TextField(validators=[MaxLengthValidator(10_000)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CardQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Speeds up "list cards in a deck, newest first" — the most common card query.
            models.Index(fields=["deck", "-created_at"], name="wayoom_card_deck_created_idx"),
        ]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Card id={self.id} name={self.name!r} deck_id={self.deck_id}>"
