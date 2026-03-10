"""Admin configuration for the WayOom bot app."""

from django.contrib import admin

from .models import Card, Deck, DeckMedia


class CardInline(admin.TabularInline):
    """Inline editor for Cards, shown directly on the Deck admin page.

    Allows viewing and editing a deck's cards without leaving the deck record.
    """

    model = Card
    extra = 0  # don't show empty placeholder rows
    readonly_fields = ["id", "created_at", "updated_at"]
    fields = ["card_type", "status", "flag", "position", "tags", "front", "back",
              "extra_notes", "due_date", "interval", "ease_factor", "review_count", "lapse_count"]


class DeckMediaInline(admin.TabularInline):
    """Inline viewer for DeckMedia, shown on the Deck admin page."""

    model = DeckMedia
    extra = 0
    readonly_fields = ["id", "original_filename", "content_type", "file_size", "created_at"]
    fields = ["original_filename", "content_type", "file_size", "created_at"]
    can_delete = True
    show_change_link = True


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    """Admin configuration for Deck."""

    list_display = ["name", "user", "is_public", "created_at"]
    list_filter = ["is_public"]
    search_fields = ["name", "description", "user__email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [CardInline, DeckMediaInline]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Admin configuration for Card."""

    list_display = ["__str__", "card_type", "status", "flag", "deck", "due_date", "created_at"]
    list_filter = ["deck", "card_type", "status", "flag"]
    search_fields = ["tags", "front", "back", "extra_notes"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(DeckMedia)
class DeckMediaAdmin(admin.ModelAdmin):
    """Admin configuration for DeckMedia."""

    list_display = ["original_filename", "deck", "content_type", "file_size", "created_at"]
    list_filter = ["content_type"]
    search_fields = ["original_filename", "deck__name"]
    readonly_fields = ["id", "created_at"]
