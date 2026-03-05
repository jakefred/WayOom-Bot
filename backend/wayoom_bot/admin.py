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
    fields = ["name", "tags", "front", "back"]


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

    list_display = ["name", "deck", "created_at"]
    list_filter = ["deck"]
    search_fields = ["name", "tags", "front", "back"]
    readonly_fields = ["id", "created_at", "updated_at"]
