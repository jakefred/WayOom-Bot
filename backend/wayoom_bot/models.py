"""Models for decks and cards used by the WayOom bot."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
import uuid


def validate_tag_list(value):
    """Ensure tags is a flat list of non-empty strings."""
    if not isinstance(value, list):
        raise ValidationError("Tags must be a list.")
    for tag in value:
        if not isinstance(tag, str) or not tag.strip():
            raise ValidationError(
                "Each tag must be a non-empty string. "
                f"Got invalid value: {tag!r}"
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Deck id={self.id} name={self.name!r} user_id={self.user_id}>"


class Card(models.Model):
    """An individual flashcard belonging to a deck.

    Cards inherit their deck's privacy — treat a card as private if its deck is.
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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Card id={self.id} name={self.name!r} deck_id={self.deck_id}>"
