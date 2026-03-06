from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from wayoom_bot.models import (
    Card,
    Deck,
    MAX_TAG_LENGTH,
    MAX_TAGS_PER_CARD,
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
        Card.objects.create(name="Card", deck=deck, front="F", back="B")
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
        card = Card.objects.create(name="C", deck=self.deck, front="F", back="B")
        self.assertIsNotNone(card.id)

    def test_str_returns_name(self):
        card = Card.objects.create(name="My Card", deck=self.deck, front="F", back="B")
        self.assertEqual(str(card), "My Card")

    def test_tags_default_to_empty_list(self):
        card = Card.objects.create(name="C", deck=self.deck, front="F", back="B")
        self.assertEqual(card.tags, [])

    def test_front_max_length_valid(self):
        card = Card(name="C", deck=self.deck, front="a" * 10_000, back="B")
        card.full_clean()  # should not raise

    def test_front_exceeding_max_length_raises(self):
        card = Card(name="C", deck=self.deck, front="a" * 10_001, back="B")
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_back_exceeding_max_length_raises(self):
        card = Card(name="C", deck=self.deck, front="F", back="a" * 10_001)
        with self.assertRaises(ValidationError):
            card.full_clean()

    def test_invalid_tags_caught_by_full_clean(self):
        card = Card(name="C", deck=self.deck, front="F", back="B", tags="not a list")
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
            name="C1", deck=cls.alice_private_deck, front="F", back="B"
        )
        cls.card_alice_public = Card.objects.create(
            name="C2", deck=cls.alice_public_deck, front="F", back="B"
        )
        cls.card_bob_private = Card.objects.create(
            name="C3", deck=cls.bob_private_deck, front="F", back="B"
        )
        cls.card_bob_public = Card.objects.create(
            name="C4", deck=cls.bob_public_deck, front="F", back="B"
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
        cls.alice_card = Card.objects.create(name="AC", deck=cls.alice_deck, front="F", back="B")
        cls.bob_card = Card.objects.create(name="BC", deck=cls.bob_deck, front="F", back="B")

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
            "name": "New Card",
            "front": "Question",
            "back": "Answer",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["deck"], self.alice_deck.id)

    def test_non_owner_cannot_create_card_in_others_deck(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.bob_deck.id), {
            "name": "Sneaky",
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_card(self):
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "name": "Nope",
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_card_tags_default_to_empty(self):
        self.client.force_authenticate(self.alice)
        resp = self.client.post(card_list_url(self.alice_deck.id), {
            "name": "No Tags",
            "front": "Q",
            "back": "A",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["tags"], [])


class CardViewUpdateDeleteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(email="alice@example.com", password="pass1234")
        cls.bob = User.objects.create_user(email="bob@example.com", password="pass1234")
        cls.alice_private_deck = Deck.objects.create(name="A Priv", user=cls.alice, is_public=False)
        cls.alice_public_deck = Deck.objects.create(name="A Pub", user=cls.alice, is_public=True)
        cls.private_card = Card.objects.create(
            name="PC", deck=cls.alice_private_deck, front="F", back="B"
        )
        cls.public_card = Card.objects.create(
            name="PubC", deck=cls.alice_public_deck, front="F", back="B"
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
