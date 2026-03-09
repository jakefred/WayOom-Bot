import io
import os
import zipfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from wayoom_bot.models import (
    Card,
    Deck,
    MAX_EXTRA_NOTE_LENGTH,
    MAX_EXTRA_NOTES,
    MAX_TAG_LENGTH,
    MAX_TAGS_PER_CARD,
    validate_extra_notes,
    validate_tag_list,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# validate_tag_list (standalone validator)
# ---------------------------------------------------------------------------

class ValidateTagListTests(TestCase):
    def test_valid_tags(self):
        validate_tag_list(["python", "django"])  # should not raise

    def test_empty_list_is_valid(self):
        validate_tag_list([])  # should not raise

    def test_non_list_raises(self):
        with self.assertRaises(ValidationError):
            validate_tag_list("not a list")

    def test_empty_string_tag_raises(self):
        with self.assertRaises(ValidationError):
            validate_tag_list(["valid", ""])

    def test_whitespace_only_tag_raises(self):
        with self.assertRaises(ValidationError):
            validate_tag_list(["valid", "   "])

    def test_non_string_tag_raises(self):
        with self.assertRaises(ValidationError):
            validate_tag_list(["valid", 123])

    def test_tag_exceeding_max_length_raises(self):
        with self.assertRaises(ValidationError):
            validate_tag_list(["a" * (MAX_TAG_LENGTH + 1)])

    def test_tag_at_max_length_is_valid(self):
        validate_tag_list(["a" * MAX_TAG_LENGTH])  # should not raise

    def test_too_many_tags_raises(self):
        with self.assertRaises(ValidationError):
            validate_tag_list(["tag"] * (MAX_TAGS_PER_CARD + 1))

    def test_max_tags_is_valid(self):
        validate_tag_list(["tag"] * MAX_TAGS_PER_CARD)  # should not raise


# ---------------------------------------------------------------------------
# validate_extra_notes (standalone validator)
# ---------------------------------------------------------------------------

class ValidateExtraNotesTests(TestCase):
    def test_valid_notes(self):
        validate_extra_notes(["Some context.", "Source: p.42"])  # should not raise

    def test_empty_list_is_valid(self):
        validate_extra_notes([])  # should not raise

    def test_blank_string_is_valid(self):
        validate_extra_notes([""])  # Anki fields can be empty

    def test_non_list_raises(self):
        with self.assertRaises(ValidationError):
            validate_extra_notes("not a list")

    def test_non_string_item_raises(self):
        with self.assertRaises(ValidationError):
            validate_extra_notes(["valid", 123])

    def test_item_exceeding_max_length_raises(self):
        with self.assertRaises(ValidationError):
            validate_extra_notes(["a" * (MAX_EXTRA_NOTE_LENGTH + 1)])

    def test_item_at_max_length_is_valid(self):
        validate_extra_notes(["a" * MAX_EXTRA_NOTE_LENGTH])  # should not raise

    def test_too_many_notes_raises(self):
        with self.assertRaises(ValidationError):
            validate_extra_notes(["note"] * (MAX_EXTRA_NOTES + 1))

    def test_max_notes_is_valid(self):
        validate_extra_notes(["note"] * MAX_EXTRA_NOTES)  # should not raise


# ---------------------------------------------------------------------------
# Deck model
# ---------------------------------------------------------------------------

class DeckModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="owner@example.com", password="pass1234")

    def test_uuid_primary_key_auto_generated(self):
        deck = Deck.objects.create(name="Test", user=self.user)
        self.assertIsNotNone(deck.id)

    def test_is_public_defaults_to_false(self):
        deck = Deck.objects.create(name="Test", user=self.user)
        self.assertFalse(deck.is_public)

    def test_str_returns_name(self):
        deck = Deck.objects.create(name="My Deck", user=self.user)
        self.assertEqual(str(deck), "My Deck")

    def test_default_ordering_is_by_created_at_desc(self):
        self.assertEqual(Deck._meta.ordering, ["-created_at"])

    def test_description_max_length_valid(self):
        deck = Deck(name="Test", user=self.user, description="a" * 2000)
        deck.full_clean()  # should not raise

    def test_description_exceeding_max_length_raises(self):
        deck = Deck(name="Test", user=self.user, description="a" * 2001)
        with self.assertRaises(ValidationError):
            deck.full_clean()

    def test_description_blank_is_valid(self):
        deck = Deck(name="Test", user=self.user, description="")
        deck.full_clean()  # should not raise

    def test_cascade_delete_removes_cards(self):
        deck = Deck.objects.create(name="Test", user=self.user)
        Card.objects.create(deck=deck, front="F", back="B")
        deck.delete()
        self.assertEqual(Card.objects.count(), 0)


# ---------------------------------------------------------------------------
# Card model
# ---------------------------------------------------------------------------

class CardModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="owner@example.com", password="pass1234")
        cls.deck = Deck.objects.create(name="Test Deck", user=cls.user)

    def test_uuid_primary_key_auto_generated(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertIsNotNone(card.id)

    def test_str_returns_truncated_front(self):
        card = Card.objects.create(deck=self.deck, front="My front text", back="B")
        self.assertEqual(str(card), "My front text")

    def test_str_truncates_long_front(self):
        card = Card.objects.create(deck=self.deck, front="a" * 100, back="B")
        self.assertEqual(str(card), "a" * 50)

    def test_tags_default_to_empty_list(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.tags, [])

    def test_front_max_length_valid(self):
        card = Card(deck=self.deck, front="a" * 10_000, back="B")
        card.full_clean()  # should not raise

    def test_front_exceeding_max_length_raises(self):
        card = Card(deck=self.deck, front="a" * 10_001, back="B")
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_back_exceeding_max_length_raises(self):
        card = Card(deck=self.deck, front="F", back="a" * 10_001)
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_invalid_tags_caught_by_full_clean(self):
        card = Card(deck=self.deck, front="F", back="B", tags="not a list")
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_card_type_defaults_to_basic(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.card_type, Card.CardType.BASIC)

    def test_card_type_basic_reversed_is_valid(self):
        card = Card(deck=self.deck, front="F", back="B", card_type=Card.CardType.BASIC_REVERSED)
        card.full_clean()  # should not raise

    def test_card_type_cloze_is_valid(self):
        card = Card(deck=self.deck, front="{{c1::answer}}", back="", card_type=Card.CardType.CLOZE)
        card.full_clean()  # should not raise

    def test_card_type_invalid_value_raises(self):
        card = Card(deck=self.deck, front="F", back="B", card_type="invalid")
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_flag_defaults_to_zero(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.flag, 0)

    def test_flag_valid_range(self):
        for value in range(8):  # 0-7 inclusive
            card = Card(deck=self.deck, front="F", back="B", flag=value)
            card.full_clean()  # should not raise

    def test_flag_above_max_raises(self):
        card = Card(deck=self.deck, front="F", back="B", flag=8)
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_position_defaults_to_null(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertIsNone(card.position)

    def test_position_can_be_set(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B", position=3)
        card.refresh_from_db()
        self.assertEqual(card.position, 3)

    def test_status_defaults_to_new(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.status, Card.CardStatus.NEW)

    def test_status_valid_choices(self):
        for choice in Card.CardStatus.values:
            card = Card(deck=self.deck, front="F", back="B", status=choice)
            card.full_clean()  # should not raise

    def test_status_invalid_value_raises(self):
        card = Card(deck=self.deck, front="F", back="B", status="invalid")
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_due_date_defaults_to_null(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertIsNone(card.due_date)

    def test_interval_defaults_to_zero(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.interval, 0)

    def test_ease_factor_defaults_to_2_5(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertAlmostEqual(card.ease_factor, 2.5)

    def test_review_count_defaults_to_zero(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.review_count, 0)

    def test_lapse_count_defaults_to_zero(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.lapse_count, 0)

    def test_extra_notes_default_to_empty_list(self):
        card = Card.objects.create(deck=self.deck, front="F", back="B")
        self.assertEqual(card.extra_notes, [])

    def test_extra_notes_stores_ordered_list(self):
        notes = ["Extra context.", "Source: p.42"]
        card = Card.objects.create(deck=self.deck, front="F", back="B", extra_notes=notes)
        card.refresh_from_db()
        self.assertEqual(card.extra_notes, notes)

    def test_extra_notes_allows_blank_strings(self):
        card = Card(deck=self.deck, front="F", back="B", extra_notes=[""])
        card.full_clean()  # should not raise

    def test_extra_notes_item_exceeding_max_length_raises(self):
        card = Card(deck=self.deck, front="F", back="B", extra_notes=["a" * (MAX_EXTRA_NOTE_LENGTH + 1)])
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_too_many_extra_notes_raises(self):
        card = Card(deck=self.deck, front="F", back="B", extra_notes=["note"] * (MAX_EXTRA_NOTES + 1))
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_invalid_extra_notes_caught_by_full_clean(self):
        card = Card(deck=self.deck, front="F", back="B", extra_notes="not a list")
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_default_ordering_is_by_created_at_desc(self):
        self.assertEqual(Card._meta.ordering, ["-created_at"])


# ---------------------------------------------------------------------------
# DeckQuerySet
# ---------------------------------------------------------------------------

class DeckQuerySetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")

        cls.alice_private = Deck.objects.create(name="Alice Private", user=cls.alice, is_public=False)
        cls.alice_public = Deck.objects.create(name="Alice Public", user=cls.alice, is_public=True)
        cls.bob_private = Deck.objects.create(name="Bob Private", user=cls.bob, is_public=False)
        cls.bob_public = Deck.objects.create(name="Bob Public", user=cls.bob, is_public=True)

    def test_visible_to_returns_own_and_public(self):
        visible = set(Deck.objects.visible_to(self.alice).values_list("id", flat=True))
        self.assertIn(self.alice_private.id, visible)
        self.assertIn(self.alice_public.id, visible)
        self.assertIn(self.bob_public.id, visible)
        self.assertNotIn(self.bob_private.id, visible)

    def test_visible_to_other_user(self):
        visible = set(Deck.objects.visible_to(self.bob).values_list("id", flat=True))
        self.assertIn(self.bob_private.id, visible)
        self.assertIn(self.bob_public.id, visible)
        self.assertIn(self.alice_public.id, visible)
        self.assertNotIn(self.alice_private.id, visible)

    def test_owned_by_returns_only_own_decks(self):
        owned = set(Deck.objects.owned_by(self.alice).values_list("id", flat=True))
        self.assertEqual(owned, {self.alice_private.id, self.alice_public.id})

    def test_owned_by_excludes_other_users(self):
        owned = set(Deck.objects.owned_by(self.bob).values_list("id", flat=True))
        self.assertNotIn(self.alice_private.id, owned)
        self.assertNotIn(self.alice_public.id, owned)


# ---------------------------------------------------------------------------
# CardQuerySet
# ---------------------------------------------------------------------------

class CardQuerySetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")

        cls.alice_private_deck = Deck.objects.create(name="A Priv", user=cls.alice, is_public=False)
        cls.alice_public_deck = Deck.objects.create(name="A Pub", user=cls.alice, is_public=True)
        cls.bob_private_deck = Deck.objects.create(name="B Priv", user=cls.bob, is_public=False)
        cls.bob_public_deck = Deck.objects.create(name="B Pub", user=cls.bob, is_public=True)

        cls.card_alice_private = Card.objects.create(
            deck=cls.alice_private_deck, front="F", back="B"
        )
        cls.card_alice_public = Card.objects.create(
            deck=cls.alice_public_deck, front="F", back="B"
        )
        cls.card_bob_private = Card.objects.create(
            deck=cls.bob_private_deck, front="F", back="B"
        )
        cls.card_bob_public = Card.objects.create(
            deck=cls.bob_public_deck, front="F", back="B"
        )

    def test_visible_to_returns_own_and_public_deck_cards(self):
        visible = set(Card.objects.visible_to(self.alice).values_list("id", flat=True))
        self.assertIn(self.card_alice_private.id, visible)
        self.assertIn(self.card_alice_public.id, visible)
        self.assertIn(self.card_bob_public.id, visible)
        self.assertNotIn(self.card_bob_private.id, visible)

    def test_visible_to_other_user(self):
        visible = set(Card.objects.visible_to(self.bob).values_list("id", flat=True))
        self.assertIn(self.card_bob_private.id, visible)
        self.assertIn(self.card_bob_public.id, visible)
        self.assertIn(self.card_alice_public.id, visible)
        self.assertNotIn(self.card_alice_private.id, visible)

    def test_owned_by_returns_only_own_deck_cards(self):
        owned = set(Card.objects.owned_by(self.alice).values_list("id", flat=True))
        self.assertEqual(owned, {self.card_alice_private.id, self.card_alice_public.id})

    def test_owned_by_excludes_other_users_cards(self):
        owned = set(Card.objects.owned_by(self.bob).values_list("id", flat=True))
        self.assertNotIn(self.card_alice_private.id, owned)
        self.assertNotIn(self.card_alice_public.id, owned)


# ===========================================================================
# View tests
# ===========================================================================

def deck_list_url():
    return "/api/decks/"


def deck_detail_url(deck_id):
    return f"/api/decks/{deck_id}/"


def card_list_url(deck_id):
    return f"/api/decks/{deck_id}/cards/"


def card_detail_url(deck_id, card_id):
    return f"/api/decks/{deck_id}/cards/{card_id}/"


# ---------------------------------------------------------------------------
# DeckViewSet
# ---------------------------------------------------------------------------

class DeckViewListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        cls.alice_private = Deck.objects.create(name="A Priv", user=cls.alice, is_public=False)
        cls.alice_public = Deck.objects.create(name="A Pub", user=cls.alice, is_public=True)
        cls.bob_private = Deck.objects.create(name="B Priv", user=cls.bob, is_public=False)

    def test_authenticated_user_sees_own_and_public(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.get(deck_list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {d["id"] for d in resp.data}
        self.assertIn(str(self.alice_private.id), ids)
        self.assertIn(str(self.alice_public.id), ids)
        self.assertNotIn(str(self.bob_private.id), ids)

    def test_anonymous_user_sees_only_public(self):
        resp = self.client.get(deck_list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {d["id"] for d in resp.data}
        self.assertIn(str(self.alice_public.id), ids)
        self.assertNotIn(str(self.alice_private.id), ids)
        self.assertNotIn(str(self.bob_private.id), ids)


class DeckViewCreateTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")

    def test_authenticated_user_can_create_deck(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(deck_list_url(), {"name": "New Deck"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "New Deck")
        self.assertEqual(resp.data["user"], self.alice.id)

    def test_anonymous_user_cannot_create_deck(self):
        resp = self.client.post(deck_list_url(), {"name": "Nope"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_field_cannot_be_overridden(self):
        bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        self.client.force_authenticate(self.alice)
        resp = self.client.post(deck_list_url(), {"name": "Stolen", "user": str(bob.id)})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["user"], self.alice.id)


class DeckViewUpdateDeleteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        cls.alice_deck = Deck.objects.create(name="Alice Deck", user=cls.alice)
        cls.alice_public_deck = Deck.objects.create(name="Alice Public", user=cls.alice, is_public=True)

    def test_owner_can_update_deck(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.patch(deck_detail_url(self.alice_deck.id), {"name": "Renamed"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Renamed")

    def test_non_owner_cannot_update_private_deck(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.patch(deck_detail_url(self.alice_deck.id), {"name": "Hijacked"})
        # Private deck is invisible to non-owners — 404 avoids leaking existence.
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_update_public_deck(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.patch(deck_detail_url(self.alice_public_deck.id), {"name": "Hijacked"})
        # Public deck is visible but not writable — 403.
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_deck(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.delete(deck_detail_url(self.alice_deck.id))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Deck.objects.filter(id=self.alice_deck.id).exists())

    def test_non_owner_cannot_delete_private_deck(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.delete(deck_detail_url(self.alice_deck.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_delete_public_deck(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.delete(deck_detail_url(self.alice_public_deck.id))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_update_deck(self):
        resp = self.client.patch(deck_detail_url(self.alice_deck.id), {"name": "Nope"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# CardViewSet
# ---------------------------------------------------------------------------

class CardViewListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        cls.alice_deck = Deck.objects.create(name="A Deck", user=cls.alice)
        cls.bob_deck = Deck.objects.create(name="B Deck", user=cls.bob, is_public=False)
        cls.alice_card = Card.objects.create(deck=cls.alice_deck, front="F", back="B")
        cls.bob_card = Card.objects.create(deck=cls.bob_deck, front="F", back="B")

    def test_owner_can_list_cards(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.get(card_list_url(self.alice_deck.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_non_owner_cannot_see_private_deck_cards(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.get(card_list_url(self.bob_deck.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_anonymous_user_is_blocked(self):
        resp = self.client.get(card_list_url(self.alice_deck.id))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class CardViewCreateTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        cls.alice_deck = Deck.objects.create(name="A Deck", user=cls.alice)
        cls.bob_deck = Deck.objects.create(name="B Deck", user=cls.bob)

    def test_owner_can_create_card(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Question",
            "back": "Answer",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["deck"], self.alice_deck.id)

    def test_non_owner_cannot_create_card_in_others_deck(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.bob_deck.id), {
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_card(self):
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_card_tags_default_to_empty(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["tags"], [])

    def test_card_type_defaults_to_basic_in_response(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["card_type"], "basic")

    def test_card_type_can_be_set_on_create(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "{{c1::answer}}",
            "back": "",
            "card_type": "cloze",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["card_type"], "cloze")

    def test_card_type_invalid_value_rejected(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
            "card_type": "invalid",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_flag_defaults_to_zero_in_response(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q", "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["flag"], 0)

    def test_flag_can_be_set_on_create(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q", "back": "A", "flag": 3,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["flag"], 3)

    def test_flag_above_max_rejected_by_api(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q", "back": "A", "flag": 8,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_position_defaults_to_null_in_response(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q", "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(resp.data["position"])

    def test_position_can_be_set_on_create(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q", "back": "A", "position": 5,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["position"], 5)

    def test_sr_fields_default_values_in_response(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "new")
        self.assertIsNone(resp.data["due_date"])
        self.assertEqual(resp.data["interval"], 0)
        self.assertAlmostEqual(float(resp.data["ease_factor"]), 2.5)
        self.assertEqual(resp.data["review_count"], 0)
        self.assertEqual(resp.data["lapse_count"], 0)

    def test_sr_fields_can_be_set_on_create(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
            "status": "review",
            "interval": 14,
            "ease_factor": 2.3,
            "review_count": 5,
            "lapse_count": 1,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "review")
        self.assertEqual(resp.data["interval"], 14)
        self.assertAlmostEqual(float(resp.data["ease_factor"]), 2.3)
        self.assertEqual(resp.data["review_count"], 5)
        self.assertEqual(resp.data["lapse_count"], 1)

    def test_status_invalid_value_rejected_by_api(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
            "status": "invalid",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_card_extra_notes_default_to_empty(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["extra_notes"], [])

    def test_card_extra_notes_saved_and_returned(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "front": "Q",
            "back": "A",
            "extra_notes": ["Hint: think about osmosis.", "Source: Ch. 3"],
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["extra_notes"], ["Hint: think about osmosis.", "Source: Ch. 3"])


class CardViewUpdateDeleteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        cls.alice_private_deck = Deck.objects.create(name="A Priv", user=cls.alice, is_public=False)
        cls.alice_public_deck = Deck.objects.create(name="A Pub", user=cls.alice, is_public=True)
        cls.private_card = Card.objects.create(
            deck=cls.alice_private_deck, front="F", back="B"
        )
        cls.public_card = Card.objects.create(
            deck=cls.alice_public_deck, front="F", back="B"
        )

    def test_owner_can_update_card(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.patch(
            card_detail_url(self.alice_private_deck.id, self.private_card.id),
            {"front": "Updated"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["front"], "Updated")

    def test_non_owner_cannot_update_private_deck_card(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.patch(
            card_detail_url(self.alice_private_deck.id, self.private_card.id),
            {"front": "Hijacked"},
        )
        # Private deck card is invisible — 404.
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_update_public_deck_card(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.patch(
            card_detail_url(self.alice_public_deck.id, self.public_card.id),
            {"front": "Hijacked"},
        )
        # Public deck card is visible but not writable — 403.
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_card(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.delete(
            card_detail_url(self.alice_private_deck.id, self.private_card.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Card.objects.filter(id=self.private_card.id).exists())

    def test_non_owner_cannot_delete_private_deck_card(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.delete(
            card_detail_url(self.alice_private_deck.id, self.private_card.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_delete_public_deck_card(self):
        self.client.force_authenticate(self.bob)
        resp = self.client.delete(
            card_detail_url(self.alice_public_deck.id, self.public_card.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_update_card(self):
        resp = self.client.patch(
            card_detail_url(self.alice_private_deck.id, self.private_card.id),
            {"front": "Nope"},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# .apkg import — helpers
# ---------------------------------------------------------------------------

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "test_fixtures")
_IMPORT_URL = reverse("import-apkg")


def _fixture(name: str) -> bytes:
    """Return the raw bytes of a test fixture .apkg file."""
    path = os.path.join(_FIXTURES_DIR, name)
    with open(path, "rb") as f:
        return f.read()


def _post_apkg(client, data: bytes, filename: str = "deck.apkg"):
    """POST an .apkg file to the import endpoint."""
    return client.post(
        _IMPORT_URL,
        {"file": io.BytesIO(data)},
        format="multipart",
        # Tell DRF what filename the upload has (used by the serializer for
        # extension validation).
        CONTENT_DISPOSITION=f'attachment; filename="{filename}"',
    )


def _post_apkg_named(client, data: bytes, filename: str):
    """POST using a named InMemoryUploadedFile so the serializer sees the filename."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    uploaded = SimpleUploadedFile(filename, data, content_type="application/octet-stream")
    return client.post(_IMPORT_URL, {"file": uploaded}, format="multipart")


# ---------------------------------------------------------------------------
# .apkg import — parser unit tests (no DB, no auth)
# ---------------------------------------------------------------------------

class ApkgParserTests(TestCase):
    """Unit-test parse_apkg() in isolation — no Django DB, no HTTP."""

    def setUp(self):
        from wayoom_bot.importers.apkg import parse_apkg
        self.parse = parse_apkg

    def test_basic_deck_parsed(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        self.assertEqual(len(result.decks), 1)
        self.assertEqual(result.decks[0]["name"], "Test Deck")
        self.assertEqual(len(result.cards), 2)
        self.assertEqual(len(result.errors), 0)

    def test_field_mapping(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        # Cards ordered by card id; guid0001 (review) was inserted first.
        card = next(c for c in result.cards if c["front"] == "What is Python?")
        self.assertEqual(card["back"], "A programming language")
        self.assertEqual(card["extra_notes"], ["Extra info"])

    def test_tags_parsed(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        card = next(c for c in result.cards if c["front"] == "What is Python?")
        self.assertIn("python", card["tags"])
        self.assertIn("programming", card["tags"])

    def test_sr_fields_mapped(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        card = next(c for c in result.cards if c["front"] == "What is Python?")
        self.assertEqual(card["status"], "review")
        self.assertEqual(card["interval"], 10)
        self.assertAlmostEqual(card["ease_factor"], 2.5)
        self.assertEqual(card["review_count"], 5)
        self.assertEqual(card["lapse_count"], 1)

    def test_due_date_conversion_review_card(self):
        """Review card (queue=2): due=100 days after collection creation."""
        from datetime import datetime, timedelta, timezone
        result = self.parse(_fixture("basic_deck.apkg"))
        card = next(c for c in result.cards if c["front"] == "What is Python?")
        crt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        expected = crt + timedelta(days=100)
        self.assertEqual(card["due_date"], expected)

    def test_new_card_has_no_due_date(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        card = next(c for c in result.cards if c["front"] == "What is Django?")
        self.assertEqual(card["status"], "new")
        self.assertIsNone(card["due_date"])

    def test_flag_extracted_from_low_bits(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        card = next(c for c in result.cards if c["front"] == "What is Python?")
        self.assertEqual(card["flag"], 2)  # orange

    def test_unflagged_card(self):
        result = self.parse(_fixture("basic_deck.apkg"))
        card = next(c for c in result.cards if c["front"] == "What is Django?")
        self.assertEqual(card["flag"], 0)

    def test_multi_deck_names_preserved(self):
        result = self.parse(_fixture("multi_deck.apkg"))
        names = {d["name"] for d in result.decks}
        self.assertIn("Languages::Python", names)
        self.assertIn("Languages::Java", names)

    def test_multi_deck_card_count(self):
        result = self.parse(_fixture("multi_deck.apkg"))
        self.assertEqual(len(result.cards), 2)
        self.assertEqual(len(result.errors), 0)

    def test_basic_card_type_detected(self):
        result = self.parse(_fixture("card_types.apkg"))
        card = next(c for c in result.cards if c["front"] == "Basic front")
        self.assertEqual(card["card_type"], "basic")

    def test_basic_reversed_card_type_detected(self):
        result = self.parse(_fixture("card_types.apkg"))
        rev_cards = [c for c in result.cards if c["front"] in ("Rev front", "Rev back")]
        self.assertEqual(len(rev_cards), 2)
        for c in rev_cards:
            self.assertEqual(c["card_type"], "basic_reversed")

    def test_cloze_card_type_detected(self):
        result = self.parse(_fixture("card_types.apkg"))
        cloze = next(c for c in result.cards if "capital" in c["front"])
        self.assertEqual(cloze["card_type"], "cloze")

    def test_deterministic_uuid(self):
        """Same file parsed twice produces identical card UUIDs."""
        r1 = self.parse(_fixture("basic_deck.apkg"))
        r2 = self.parse(_fixture("basic_deck.apkg"))
        ids1 = {c["id"] for c in r1.cards}
        ids2 = {c["id"] for c in r2.cards}
        self.assertEqual(ids1, ids2)

    def test_invalid_zip_raises(self):
        from wayoom_bot.importers.apkg import parse_apkg
        with self.assertRaises(ValueError):
            parse_apkg(b"not a zip file")

    def test_partial_failure_skips_bad_card(self):
        """A card referencing an unknown model ID is skipped, others succeed."""
        import json
        import sqlite3
        import tempfile

        # Build a minimal .apkg with one valid note and one with a bad model ID.
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE col (id INTEGER PRIMARY KEY, crt INTEGER NOT NULL,
                mod INTEGER NOT NULL, scm INTEGER NOT NULL, ver INTEGER NOT NULL,
                dty INTEGER NOT NULL, usn INTEGER NOT NULL, ls INTEGER NOT NULL,
                conf TEXT NOT NULL, models TEXT NOT NULL, decks TEXT NOT NULL,
                dconf TEXT NOT NULL, tags TEXT NOT NULL);
            CREATE TABLE notes (id INTEGER PRIMARY KEY, guid TEXT NOT NULL,
                mid INTEGER NOT NULL, mod INTEGER NOT NULL, usn INTEGER NOT NULL,
                tags TEXT NOT NULL, flds TEXT NOT NULL, sfld TEXT NOT NULL,
                csum INTEGER NOT NULL, flags INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE cards (id INTEGER PRIMARY KEY, nid INTEGER NOT NULL,
                did INTEGER NOT NULL, ord INTEGER NOT NULL, mod INTEGER NOT NULL,
                usn INTEGER NOT NULL, type INTEGER NOT NULL, queue INTEGER NOT NULL,
                due INTEGER NOT NULL, ivl INTEGER NOT NULL, factor INTEGER NOT NULL,
                reps INTEGER NOT NULL, lapses INTEGER NOT NULL, left INTEGER NOT NULL,
                odue INTEGER NOT NULL, odid INTEGER NOT NULL, flags INTEGER NOT NULL,
                data TEXT NOT NULL);
            CREATE TABLE revlog (id INTEGER PRIMARY KEY, cid INTEGER NOT NULL,
                usn INTEGER NOT NULL, ease INTEGER NOT NULL, ivl INTEGER NOT NULL,
                lastIvl INTEGER NOT NULL, factor INTEGER NOT NULL, time INTEGER NOT NULL,
                type INTEGER NOT NULL);
            CREATE TABLE graves (usn INTEGER NOT NULL, oid INTEGER NOT NULL, type INTEGER NOT NULL);
        """)
        mid = 9999001
        did = 9999002
        models = {str(mid): {"id": mid, "name": "Basic",
                              "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
                              "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Front}}", "afmt": "{{Back}}"}]}}
        decks = {str(did): {"id": did, "name": "Partial Deck"}}
        CRT = 1704067200
        conn.execute(
            "INSERT INTO col VALUES (1,?,?,?,11,0,0,0,'{}',?,?,'{}','{}')",
            (CRT, CRT, CRT, json.dumps(models), json.dumps(decks)),
        )
        # Valid note
        conn.execute("INSERT INTO notes VALUES (1,'pguid001',?,?,0,'','Front\x1fBack','Front',0,0,'')", (mid, CRT))
        conn.execute("INSERT INTO cards VALUES (1,1,?,0,?,0,2,2,10,7,2500,2,0,0,0,0,0,'')", (did, CRT))
        # Note with a BAD model ID (not in models dict)
        conn.execute("INSERT INTO notes VALUES (2,'pguid002',99999,?,0,'','Bad\x1fNote','Bad',0,0,'')", (CRT,))
        conn.execute("INSERT INTO cards VALUES (2,2,?,0,?,0,0,0,1,0,0,0,0,0,0,0,0,'')", (did, CRT))
        conn.commit()

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        try:
            bk = sqlite3.connect(tmp.name)
            conn.backup(bk)
            bk.close()
            with open(tmp.name, "rb") as f:
                sqlite_bytes = f.read()
        finally:
            import os as _os
            _os.unlink(tmp.name)
        conn.close()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("collection.anki21", sqlite_bytes)
            zf.writestr("media", "{}")
        apkg = buf.getvalue()

        from wayoom_bot.importers.apkg import parse_apkg
        result = parse_apkg(apkg)
        self.assertEqual(len(result.cards), 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("pguid002", result.errors[0])


# ---------------------------------------------------------------------------
# .apkg import — API endpoint tests
# ---------------------------------------------------------------------------

class ApkgImportViewTests(APITestCase):
    """Integration tests for POST /api/import/apkg/."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="importer", email="importer@example.com", password="pass"
        )
        self.client.force_authenticate(user=self.user)

    def test_successful_import(self):
        resp = _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["decks_created"], 1)
        self.assertEqual(data["cards_created"], 2)
        self.assertEqual(data["cards_skipped"], 0)
        self.assertEqual(data["errors"], [])

    def test_decks_and_cards_saved_to_db(self):
        _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        self.assertEqual(Deck.objects.filter(user=self.user).count(), 1)
        deck = Deck.objects.get(user=self.user)
        self.assertEqual(deck.name, "Test Deck")
        self.assertEqual(Card.objects.filter(deck=deck).count(), 2)

    def test_duplicate_import_skips_cards(self):
        _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        resp = _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["decks_created"], 0)
        self.assertEqual(data["cards_created"], 0)
        self.assertEqual(data["cards_skipped"], 2)
        # Total cards in DB should still be 2, not 4
        self.assertEqual(Card.objects.filter(deck__user=self.user).count(), 2)

    def test_multi_deck_import(self):
        resp = _post_apkg_named(self.client, _fixture("multi_deck.apkg"), "multi_deck.apkg")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["decks_created"], 2)
        self.assertEqual(data["cards_created"], 2)

    def test_deck_names_preserved(self):
        _post_apkg_named(self.client, _fixture("multi_deck.apkg"), "multi_deck.apkg")
        names = set(Deck.objects.filter(user=self.user).values_list("name", flat=True))
        self.assertIn("Languages::Python", names)
        self.assertIn("Languages::Java", names)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        resp = _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_extension_returns_400(self):
        resp = _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "deck.txt")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_zip_returns_400(self):
        resp = _post_apkg_named(self.client, b"not a zip file", "bad.apkg")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_too_large_returns_400(self):
        # Build a fake .apkg that reports a large size via a mock upload.
        from django.core.files.uploadedfile import SimpleUploadedFile
        large = SimpleUploadedFile("big.apkg", b"x", content_type="application/octet-stream")
        # Patch the size attribute to exceed 50 MB
        large.size = 51 * 1024 * 1024
        resp = self.client.post(_IMPORT_URL, {"file": large}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_two_users_import_same_file_get_separate_decks(self):
        user2 = User.objects.create_user(
            username="importer2", email="importer2@example.com", password="pass"
        )
        _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        self.client.force_authenticate(user=user2)
        resp = _post_apkg_named(self.client, _fixture("basic_deck.apkg"), "basic_deck.apkg")
        self.assertEqual(resp.json()["decks_created"], 1)
        self.assertEqual(resp.json()["cards_created"], 2)
        # Each user should have their own deck
        self.assertEqual(Deck.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Deck.objects.filter(user=user2).count(), 1)
        self.assertNotEqual(
            Deck.objects.get(user=self.user).id,
            Deck.objects.get(user=user2).id,
        )
