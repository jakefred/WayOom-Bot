"""Serializers for the users app.

RegisterSerializer handles new account creation.  It validates the two
passwords match, runs Django's built-in password strength validators, and
then creates the user — keeping all that logic out of the view.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Validate and create a new user account.

    Expects:
        email     — must be unique
        password  — must pass Django's AUTH_PASSWORD_VALIDATORS
        password2 — confirmation; must match password

    Returns the created User instance (password2 is write-only and not
    included in the output).
    """

    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = ["email", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        # Run Django's built-in validators (minimum length, common passwords, etc.)
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
