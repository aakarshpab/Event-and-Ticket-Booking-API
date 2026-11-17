"""Central role-based permission classes. Reuse these in every app."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    message = "Admin access required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_admin_role)


class IsOrganizerRole(BasePermission):
    message = "Only organizers can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_organizer)


class IsAttendeeRole(BasePermission):
    message = "Only attendees can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_attendee)


class IsOrganizerOrAdmin(BasePermission):
    message = "Only organizers or admins can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_organizer or u.is_admin_role))


class IsOrganizerOrAdminOrReadOnly(IsOrganizerOrAdmin):
    """Any logged-in user can read; only organizers/admins can write."""

    message = "Attendees have read-only access."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)
