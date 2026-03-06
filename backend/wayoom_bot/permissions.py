"""Custom DRF permission classes for the wayoom_bot app.

All ownership checks live here so they are easy to test in isolation and
can be reused across views without duplicating logic.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """Object-level permission: read access for visible objects; write access only for the owner.

    This works in tandem with the view's get_queryset(), which already filters
    objects to those visible to the requesting user.  This class then adds a
    second gate: safe (read) methods are always allowed, but mutating methods
    (POST, PUT, PATCH, DELETE) are only allowed when the requesting user owns
    the object.

    Works for both Deck (ownership via obj.user) and Card (ownership via
    obj.deck.user).  The select_related call in the view's queryset prevents
    an extra database hit when checking card ownership.
    """

    def has_object_permission(self, request, view, obj):
        # Safe methods are always allowed — the queryset already ensured
        # the object is visible to this user.
        if request.method in SAFE_METHODS:
            return True

        # Deck: user field is a direct FK on the model.
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Card: ownership is inherited through the parent deck.
        if hasattr(obj, "deck"):
            return obj.deck.user == request.user

        return False
