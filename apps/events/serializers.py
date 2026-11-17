from django.utils import timezone
from rest_framework import serializers

from .models import Event, TicketType, Venue


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "address", "city", "capacity"]


class TicketTypeSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = TicketType
        fields = ["id", "event", "name", "price", "quantity_total", "quantity_sold", "available"]
        read_only_fields = ["quantity_sold"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_event(self, event):
        user = self.context["request"].user
        if not (user.is_admin_role or event.organizer_id == user.id):
            raise serializers.ValidationError("You can only add ticket types to your own events.")
        if self.instance and event != self.instance.event:
            raise serializers.ValidationError("You cannot move a ticket type to another event.")
        return event

    def validate(self, attrs):
        total = attrs.get("quantity_total")
        if self.instance and total is not None and total < self.instance.quantity_sold:
            raise serializers.ValidationError(
                {"quantity_total": "Cannot be lower than tickets already sold."}
            )
        return attrs


class EventSerializer(serializers.ModelSerializer):
    # READ: full venue details. WRITE: just send "venue_id".
    venue = VenueSerializer(read_only=True)
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(), source="venue", write_only=True
    )
    organizer = serializers.StringRelatedField(read_only=True)
    ticket_types = TicketTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id", "title", "description", "category", "venue", "venue_id",
            "start_time", "end_time", "is_published", "organizer",
            "ticket_types", "created_at",
        ]

    # field-level validation
    def validate_start_time(self, value):
        changed = self.instance is None or value != self.instance.start_time
        if changed and value < timezone.now():
            raise serializers.ValidationError("Events cannot be in the past.")
        return value

    # object-level validation
    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs
