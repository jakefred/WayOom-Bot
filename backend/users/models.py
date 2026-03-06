"""
Custom user model with email as the login identifier.

Uses AbstractUser so we keep the same permissions and admin behavior as the
default User, while identifying users by email instead of username.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for the custom User model; creates users by email."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        if not password:
            raise ValueError("Users must have a password.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractUser):
    """
    User model with email as the unique login identifier.

    Username is kept for compatibility (e.g. admin) but is optional and can
    be auto-set from email. Use get_username() or .email for the login id.
    """

    email = models.EmailField("email address", unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
