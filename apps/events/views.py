from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.accounts.permissions import IsAttendeeRole
from apps.bookings.serializers import BookingRequestSerializer, BookingSerializer
from apps.bookings.services import create_booking, event_stats
from step1etm.throttles import BookingRateThrottle

from .filters import EventFilter
from .models import Event, TicketType, Venue
from .permissions import (
    IsEventOwnerOrAdmin,
    IsEventOwnerOrAdminOrReadOnly,
    IsOrganizerOrAdminOrReadOnly,
)
from .serializers import EventSerializer, TicketTypeSerializer, VenueSerializer


def visible_events_for(user):
    """Admin sees all. Organizer sees published + their own. Attendee sees published only."""
    qs = Event.objects.select_related("venue", "organizer").prefetch_related("ticket_types")
    if user.is_admin_role:
        return qs
    if user.is_organizer:
        return qs.filter(Q(is_published=True) | Q(organizer=user))
    return qs.filter(is_published=True)


class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all().order_by("name")
    serializer_class = VenueSerializer
    permission_classes = [IsOrganizerOrAdminOrReadOnly]
    search_fields = ["name", "city"]
    ordering_fields = ["name", "city", "capacity"]


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    filterset_class = EventFilter
    search_fields = ["title", "venue__city"]
    ordering_fields = ["start_time", "created_at", "title"]
    ordering = ["start_time"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # lets Swagger generate docs
            return Event.objects.none()
        return visible_events_for(self.request.user)

    def get_permissions(self):
        if self.action == "book":
            return [IsAuthenticated(), IsAttendeeRole()]
        if self.action == "stats":
            return [IsAuthenticated(), IsEventOwnerOrAdmin()]
        return [IsEventOwnerOrAdminOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @extend_schema(request=BookingRequestSerializer, responses={201: BookingSerializer})
    @action(
        detail=True, methods=["post"],
        throttle_classes=[UserRateThrottle, BookingRateThrottle],
    )
    def book(self, request, pk=None):
        """POST /events/{id}/book/  body: {"items": [{"ticket_type": 1, "quantity": 2}]}"""
        event = self.get_object()
        serializer = BookingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = create_booking(
            user=request.user, event=event, items=serializer.validated_data["items"]
        )
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """GET /events/{id}/stats/  (organizer of the event or admin only)"""
        event = self.get_object()
        return Response(event_stats(event))


class TicketTypeViewSet(viewsets.ModelViewSet):
    serializer_class = TicketTypeSerializer
    permission_classes = [IsEventOwnerOrAdminOrReadOnly]
    filterset_fields = ["event"]
    ordering_fields = ["price", "name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # lets Swagger generate docs
            return TicketType.objects.none()
        events = visible_events_for(self.request.user)
        return TicketType.objects.filter(event__in=events).select_related("event")
