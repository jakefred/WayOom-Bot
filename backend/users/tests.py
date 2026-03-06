from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


class UserManagerCreateUserTests(TestCase):
    def test_create_user_with_email(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="test@EXAMPLE.COM", password="testpass123")
        self.assertEqual(user.email, "test@example.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="testpass123")

    def test_create_user_sets_username_from_email(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.assertEqual(user.username, "test@example.com")


class UserManagerCreateSuperuserTests(TestCase):
    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="adminpass123")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_is_staff_false_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_staff=False
            )

    def test_create_superuser_is_superuser_false_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_superuser=False
            )


class UserModelTests(TestCase):
    def test_email_is_unique(self):
        User.objects.create_user(email="dupe@example.com", password="testpass123")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dupe@example.com", password="otherpass123")

    def test_str_returns_email(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.assertEqual(str(user), "test@example.com")

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
