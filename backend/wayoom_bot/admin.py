"""Admin configuration for the WayOom bot app."""

from django.contrib import admin

from .models import Card, Deck


class CardInline(admin.TabularInline):
    """Inline editor for Cards, shown directly on the Deck admin page.

    Allows viewing and editing a deck's cards without leaving the deck record.
    """

    model = Card
    extra = 0  # don't show empty placeholder rows
    readonly_fields = ["id", "created_at", "updated_at"]
    fields = ["card_type", "status", "flag", "position", "tags", "front", "back",
              "extra_notes", "due_date", "interval", "ease_factor", "review_count", "lapse_count"]


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    """Admin configuration for Deck."""

    list_display = ["name", "user", "is_public", "created_at"]
    list_filter = ["is_public"]
    search_fields = ["name", "description", "user__email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [CardInline]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Admin configuration for Card."""

    list_display = ["__str__", "card_type", "status", "flag", "deck", "due_date", "created_at"]
    list_filter = ["deck", "card_type", "status", "flag"]
    search_fields = ["front", "back", "extra_notes"]
    readonly_fields = ["id", "created_at", "updated_at"]
