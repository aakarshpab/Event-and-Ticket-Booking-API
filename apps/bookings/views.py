from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking
from .permissions import IsBookingOwnerOrAdmin
from .serializers import BookingSerializer
from .services import cancel_booking


class BookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """List/retrieve your bookings. Create bookings with POST /events/{id}/book/."""

    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsBookingOwnerOrAdmin]
    filterset_fields = ["status", "event"]
    ordering_fields = ["created_at", "total_amount"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # lets Swagger generate docs
            return Booking.objects.none()
        qs = Booking.objects.select_related("event", "payment").prefetch_related("items__ticket_type")
        user = self.request.user
        if user.is_admin_role:
            return qs
        return qs.filter(attendee=user)  # users only ever see their OWN bookings

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = cancel_booking(self.get_object())
        return Response(BookingSerializer(booking).data)
