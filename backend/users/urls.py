"""Auth URL patterns for the users app.

All routes are mounted under /api/auth/ by config/urls.py.

    POST /api/auth/register/       create account → {access, refresh}
    POST /api/auth/token/          login          → {access, refresh}
    POST /api/auth/token/refresh/  rotate tokens  → {access, refresh}
    POST /api/auth/token/verify/   check validity → 200 OK / 401
    POST /api/auth/logout/         blacklist the refresh token → 200 OK
"""

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import RegisterView

urlpatterns = [
    path("register/",      RegisterView.as_view(),        name="auth-register"),
    path("token/",         TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(),    name="token-refresh"),
    path("token/verify/",  TokenVerifyView.as_view(),     name="token-verify"),
    path("logout/",        TokenBlacklistView.as_view(),  name="auth-logout"),
]
