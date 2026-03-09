"""
DRF serializers for Deck and Card.

Validate request input and shape responses. Read-only fields (id, user, timestamps)
are never accepted from clients; views set user from request.user.
"""

from rest_framework import serializers

from .models import Card, Deck


class CardSerializer(serializers.ModelSerializer):
    """Serialize Card for API read/write. Tags must be a list of non-empty strings."""

    tags = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
        required=False,
        default=list,
    )
    extra_notes = serializers.ListField(
        child=serializers.CharField(max_length=10_000, allow_blank=True),
        allow_empty=True,
        required=False,
        default=list,
    )

    class Meta:
        model = Card
        fields = [
            "id",
            "deck",
            "card_type",
            "status",
            "flag",
            "position",
            "tags",
            "front",
            "back",
            "extra_notes",
            "due_date",
            "interval",
            "ease_factor",
            "review_count",
            "lapse_count",
            "created_at",
            "updated_at",
        ]
        # deck is set from the URL in the view's perform_create; clients cannot
        # move a card to a different deck by supplying a deck value in the body.
        read_only_fields = ["id", "deck", "created_at", "updated_at"]
        extra_kwargs = {
            "front": {"max_length": 10_000},
            "back": {"max_length": 10_000, "allow_blank": True},
        }

    def validate_extra_notes(self, value):
        """Require a list of strings. Blank strings are allowed — Anki fields can be empty."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Extra notes must be a list.")
        for note in value:
            if not isinstance(note, str):
                raise serializers.ValidationError(
                    f"Each extra note must be a string. Got {type(note).__name__}."
                )
            if len(note) > 10_000:
                raise serializers.ValidationError(
                    "Each extra note must be at most 10,000 characters."
                )
        return value

    def validate_tags(self, value):
        """Require a list of non-empty strings. Prevents malformed or abusive payloads."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list.")
        for tag in value:
            if not isinstance(tag, str):
                raise serializers.ValidationError(
                    f"Each tag must be a string. Got {type(tag).__name__}."
                )
            if not tag.strip():
                raise serializers.ValidationError("Tags cannot contain empty strings.")
            if len(tag) > 100:
                raise serializers.ValidationError(
                    f"Tag {tag[:50]!r}... exceeds 100 characters."
                )
        return value


class ApkgImportSerializer(serializers.Serializer):
    """Validates the file upload for the .apkg import endpoint."""

    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.lower().endswith(".apkg"):
            raise serializers.ValidationError("File must have a .apkg extension.")
        max_bytes = 50 * 1024 * 1024  # 50 MB
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File is too large ({value.size / 1024 / 1024:.1f} MB). Maximum is 50 MB."
            )
        return value


class DeckSerializer(serializers.ModelSerializer):
    """
    Serialize Deck for API read/write.

    user is read-only; views must set it from request.user so clients cannot
    assign decks to other users.
    """

    class Meta:
        model = Deck
        fields = [
            "id",
            "name",
            "user",
            "description",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]
        extra_kwargs = {
            "description": {
                "max_length": 2_000,
                "allow_blank": True,
                "allow_null": True,
                "required": False,
            },
        }
