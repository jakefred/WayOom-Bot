from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

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
