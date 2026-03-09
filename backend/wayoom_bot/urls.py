"""URL routing for the wayoom_bot app.

Deck routes are registered with DefaultRouter which auto-generates:
    /api/decks/           GET (list)  POST (create)
    /api/decks/<uuid>/    GET (retrieve)  PUT/PATCH (update)  DELETE

Card routes are added manually as nested paths so cards always live under
their parent deck in the URL.  This scoping makes ownership unambiguous and
avoids pulling in the drf-nested-routers dependency.

    /api/decks/<deck_pk>/cards/           GET (list)  POST (create)
    /api/decks/<deck_pk>/cards/<uuid>/    GET (retrieve)  PUT/PATCH  DELETE

All routes are mounted under /api/ by config/urls.py.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("decks", views.DeckViewSet, basename="deck")

urlpatterns = router.urls + [
    path(
        "import/apkg/",
        views.ApkgImportView.as_view(),
        name="import-apkg",
    ),
    path(
        "decks/<uuid:deck_pk>/cards/",
        views.CardViewSet.as_view({"get": "list", "post": "create"}),
        name="card-list",
    ),
    path(
        "decks/<uuid:deck_pk>/cards/<uuid:pk>/",
        views.CardViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="card-detail",
    ),
]
