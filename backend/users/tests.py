from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = "/api/auth/register/"


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

    def test_create_user_without_password_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="test@example.com", password=None)

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


# ---------------------------------------------------------------------------
# RegisterView
# ---------------------------------------------------------------------------

class RegisterViewTests(APITestCase):
    def test_register_success(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "strongpass123!",
            "password2": "strongpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_register_missing_email(self):
        resp = self.client.post(REGISTER_URL, {
            "password": "strongpass123!",
            "password2": "strongpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password2": "strongpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password2(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "strongpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_passwords_do_not_match(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "strongpass123!",
            "password2": "differentpass456!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password_rejected(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "123",
            "password2": "123",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_common_password_rejected(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "password",
            "password2": "password",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(email="taken@example.com", password="strongpass123!")
        resp = self.client.post(REGISTER_URL, {
            "email": "taken@example.com",
            "password": "strongpass123!",
            "password2": "strongpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_cannot_set_is_staff(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "sneaky@example.com",
            "password": "strongpass123!",
            "password2": "strongpass123!",
            "is_staff": True,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="sneaky@example.com")
        self.assertFalse(user.is_staff)

    def test_register_cannot_set_is_superuser(self):
        resp = self.client.post(REGISTER_URL, {
            "email": "sneaky@example.com",
            "password": "strongpass123!",
            "password2": "strongpass123!",
            "is_superuser": True,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="sneaky@example.com")
        self.assertFalse(user.is_superuser)
