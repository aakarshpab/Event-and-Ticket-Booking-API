from rest_framework.permissions import BasePermission


class IsBookingOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_admin_role or obj.attendee_id == request.user.id
