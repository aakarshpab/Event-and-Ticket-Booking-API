from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.permissions import IsOrganizerOrAdminOrReadOnly  # noqa: F401


def _event_of(obj):
    # works for both an Event and a TicketType
    return getattr(obj, "event", obj)


class IsEventOwnerOrAdminOrReadOnly(IsOrganizerOrAdminOrReadOnly):
    """Only the organizer who created the event (or an admin) can edit/delete it."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin_role or _event_of(obj).organizer_id == request.user.id


class IsEventOwnerOrAdmin(BasePermission):
    """Used for the stats endpoint: owner or admin only (even for GET)."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_admin_role or _event_of(obj).organizer_id == request.user.id
