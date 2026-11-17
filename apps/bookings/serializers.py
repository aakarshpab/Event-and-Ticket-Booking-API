from rest_framework import serializers

from .models import Booking, BookingItem


class BookingItemInputSerializer(serializers.Serializer):
    ticket_type = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class BookingRequestSerializer(serializers.Serializer):
    items = BookingItemInputSerializer(many=True, allow_empty=False)


class BookingItemSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.CharField(source="ticket_type.name", read_only=True)

    class Meta:
        model = BookingItem
        fields = ["id", "ticket_type", "ticket_type_name", "quantity", "unit_price"]


class BookingSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True, read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True)
    payment_status = serializers.CharField(source="payment.status", read_only=True, default=None)

    class Meta:
        model = Booking
        fields = [
            "id", "event", "event_title", "status", "total_amount",
            "payment_status", "created_at", "cancelled_at", "items",
        ]
