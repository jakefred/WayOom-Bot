"""API views for Deck and Card resources.

Ownership enforcement strategy:
- get_queryset() scopes the initial queryset so users can only see objects they
  are allowed to read (own or public).
- IsOwnerOrReadOnly provides a second gate at the object level, blocking writes
  on objects the requesting user does not own.
- perform_create() injects server-controlled fields (user, deck) so clients can
  never self-assign ownership.
"""

from django.core.files.base import ContentFile
from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .importers.apkg import parse_apkg
from .models import Card, Deck, DeckMedia
from .permissions import IsOwnerOrReadOnly
from .serializers import ApkgImportSerializer, CardSerializer, DeckSerializer


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


@extend_schema(
    summary="Import an Anki .apkg file",
    description=(
        "Upload an Anki .apkg file. Creates one Deck per Anki deck found in the "
        "package and bulk-creates all cards. Duplicate cards (same Anki GUID + "
        "template ordinal) are silently skipped via deterministic UUID dedup. "
        "Partial failures are collected and returned rather than aborting the import."
    ),
    request={"multipart/form-data": ApkgImportSerializer},
    responses={
        200: OpenApiResponse(description="Import summary with counts and any errors."),
        400: OpenApiResponse(description="Invalid file (wrong extension, too large, corrupt)."),
    },
)
class ApkgImportView(APIView):
    """POST /api/import/apkg/ — import an Anki .apkg file for the authenticated user."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = ApkgImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data["file"]
        file_bytes = uploaded.read()

        try:
            parse_result = parse_apkg(file_bytes)
        except (ValueError, ImportError) as exc:
            return Response({"detail": str(exc)}, status=400)

        decks_created = 0
        cards_created = 0
        cards_skipped = 0
        media_created = 0
        media_skipped = 0
        errors = list(parse_result.errors)

        with transaction.atomic():
            # Build a map from Anki deck ID → saved Deck object.
            anki_id_to_deck: dict[int, Deck] = {}

            for deck_kwargs in parse_result.decks:
                anki_id = deck_kwargs.pop("_anki_id")
                from .importers.apkg import _anki_deck_uuid
                deck_uuid = _anki_deck_uuid(anki_id, request.user.pk)
                deck, created = Deck.objects.get_or_create(
                    id=deck_uuid,
                    defaults={
                        **deck_kwargs,
                        "user": request.user,
                        "is_public": False,
                    },
                )
                if created:
                    decks_created += 1
                anki_id_to_deck[anki_id] = deck

            # Resolve deck FK on each card and bulk-create with dedup.
            # Re-derive the card UUID scoped through the deck UUID so that two
            # users importing the same .apkg get distinct card PKs (their decks
            # already have distinct UUIDs via _anki_deck_uuid).
            card_objects = []
            for card_kwargs in parse_result.cards:
                anki_deck_id = card_kwargs.pop("_deck_anki_id")
                deck = anki_id_to_deck.get(anki_deck_id)
                if deck is None:
                    errors.append(
                        f"Card {card_kwargs.get('id')} references unknown deck {anki_deck_id}."
                    )
                    continue
                import uuid as _uuid
                from .importers.apkg import _WAYOOM_NAMESPACE
                scoped_id = _uuid.uuid5(_WAYOOM_NAMESPACE, f"{deck.id}:{card_kwargs['id']}")
                card_kwargs["id"] = scoped_id
                card_objects.append(Card(deck=deck, **card_kwargs))

            # bulk_create(ignore_conflicts=True) returns all objects passed in,
            # not just those actually inserted. Count via DB diff instead.
            existing_ids = set(
                Card.objects.filter(
                    id__in=[c.id for c in card_objects]
                ).values_list("id", flat=True)
            )
            cards_skipped = len(existing_ids)
            Card.objects.bulk_create(card_objects, ignore_conflicts=True)
            cards_created = len(card_objects) - cards_skipped

            # Save media files for every deck in the import.
            # Anki media is collection-scoped, so each file is associated with
            # all decks.  get_or_create on (deck, original_filename) deduplicates
            # re-imports safely — the first import wins.
            all_decks = list(anki_id_to_deck.values())
            for media_entry in parse_result.media:
                original_filename = media_entry["original_filename"]
                file_bytes = media_entry["file_bytes"]
                for deck in all_decks:
                    _, created = DeckMedia.objects.get_or_create(
                        deck=deck,
                        original_filename=original_filename,
                        defaults={"file_size": len(file_bytes)},
                    )
                    if created:
                        # Fetch the newly created object so we can save the file
                        # through the FileField (get_or_create doesn't return
                        # the instance in a state ready for file attachment).
                        dm = DeckMedia.objects.get(deck=deck, original_filename=original_filename)
                        dm.file.save(
                            original_filename,
                            ContentFile(file_bytes),
                            save=True,
                        )
                        media_created += 1
                    else:
                        media_skipped += 1

        return Response(
            {
                "decks_created": decks_created,
                "cards_created": cards_created,
                "cards_skipped": cards_skipped,
                "media_created": media_created,
                "media_skipped": media_skipped,
                "errors": errors,
            }
        )


@extend_schema(
    summary="Serve a deck media file",
    description=(
        "Return a media file (image, audio, etc.) attached to a deck. "
        "Access follows the deck's visibility — public deck media is readable "
        "without authentication; private deck media requires the owner's token."
    ),
    responses={
        200: OpenApiResponse(description="File contents with correct Content-Type."),
        404: OpenApiResponse(description="File not found or not visible to you."),
    },
)
class DeckMediaView(APIView):
    """GET /api/decks/<deck_pk>/media/<filename>/ — serve a deck media file."""

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, deck_pk, filename):
        user = request.user
        qs = DeckMedia.objects.select_related("deck")
        if user.is_authenticated:
            qs = qs.visible_to(user)
        else:
            qs = qs.filter(deck__is_public=True)

        try:
            media = qs.get(deck_id=deck_pk, original_filename=filename)
        except DeckMedia.DoesNotExist:
            raise NotFound("Media file not found.")

        response = FileResponse(
            media.file.open("rb"),
            content_type=media.content_type or "application/octet-stream",
        )
        response["Content-Disposition"] = f'inline; filename="{media.original_filename}"'
        return response
