"""Views for the users app.

RegisterView is the only custom view here.  All other auth endpoints
(login, refresh, verify, logout) are provided directly by SimpleJWT and
wired up in users/urls.py.
"""

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer


class RegisterView(CreateAPIView):
    """Create a new user account and return a JWT token pair.

    Returning tokens immediately on registration avoids a second round-trip:
    the frontend can consider the user logged in as soon as registration succeeds.

    Permission: AllowAny — unauthenticated users must be able to reach this endpoint.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate a token pair for the newly created user.
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )
