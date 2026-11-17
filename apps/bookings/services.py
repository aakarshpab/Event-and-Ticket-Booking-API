"""Business logic for bookings lives here (not in views), so it is easy to test."""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.events.models import TicketType
from apps.payments.models import Payment

from .models import Booking, BookingItem

CANCEL_WINDOW = timedelta(hours=24)


class BookingError(APIException):
    status_code = 400
    default_detail = "Booking failed."
    default_code = "booking_error"


@transaction.atomic
def create_booking(*, user, event, items):
    """All-or-nothing. If anything fails, the whole transaction is rolled back."""
    if not event.is_published:
        raise BookingError("This event is not open for booking.")
    if event.start_time <= timezone.now():
        raise BookingError("This event has already started.")

    # merge duplicates, e.g. the same ticket type listed twice
    wanted = {}
    for item in items:
        wanted[item["ticket_type"]] = wanted.get(item["ticket_type"], 0) + item["quantity"]

    # select_for_update() LOCKS these rows until the transaction ends, so two
    # people can't buy the last ticket at the same moment. (order_by id avoids deadlocks)
    locked = TicketType.objects.select_for_update().filter(event=event, id__in=wanted.keys()).order_by("id")
    ticket_types = {tt.id: tt for tt in locked}

    missing = set(wanted) - set(ticket_types)
    if missing:
        raise BookingError(f"Ticket type(s) {sorted(missing)} do not belong to this event.")

    booking = Booking.objects.create(attendee=user, event=event, status=Booking.Status.CONFIRMED)
    total = Decimal("0")
    for tt_id, qty in wanted.items():
        tt = ticket_types[tt_id]
        if qty > tt.available:
            raise BookingError(f"Only {tt.available} '{tt.name}' ticket(s) left.")
        tt.quantity_sold += qty
        tt.save(update_fields=["quantity_sold"])
        BookingItem.objects.create(booking=booking, ticket_type=tt, quantity=qty, unit_price=tt.price)
        total += tt.price * qty

    booking.total_amount = total
    booking.save(update_fields=["total_amount"])
    Payment.objects.create(booking=booking, amount=total, status=Payment.Status.PAID)  # mock
    return booking


@transaction.atomic
def cancel_booking(booking):
    booking = Booking.objects.select_for_update().select_related("event").get(pk=booking.pk)
    if booking.status == Booking.Status.CANCELLED:
        raise BookingError("This booking is already cancelled.")
    if booking.event.start_time - timezone.now() < CANCEL_WINDOW:
        raise BookingError("Bookings can only be cancelled up to 24 hours before the event.")

    items = list(booking.items.all())
    list(TicketType.objects.select_for_update().filter(id__in=[i.ticket_type_id for i in items]).order_by("id"))
    for item in items:  # give the tickets back
        TicketType.objects.filter(pk=item.ticket_type_id).update(
            quantity_sold=F("quantity_sold") - item.quantity
        )

    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.save(update_fields=["status", "cancelled_at"])
    Payment.objects.filter(booking=booking).update(status=Payment.Status.REFUNDED)
    return booking


def event_stats(event):
    """Tickets sold, revenue and sales per ticket type (confirmed bookings only)."""
    money = DecimalField(max_digits=14, decimal_places=2)
    line_total = ExpressionWrapper(F("quantity") * F("unit_price"), output_field=money)
    confirmed = BookingItem.objects.filter(
        booking__event=event, booking__status=Booking.Status.CONFIRMED
    )
    totals = confirmed.aggregate(
        tickets_sold=Coalesce(Sum("quantity"), 0),
        revenue=Coalesce(Sum(line_total), Value(Decimal("0")), output_field=money),
    )

    ok = Q(booking_items__booking__status=Booking.Status.CONFIRMED)
    per_type_total = ExpressionWrapper(
        F("booking_items__quantity") * F("booking_items__unit_price"), output_field=money
    )
    per_type = (
        TicketType.objects.filter(event=event)
        .annotate(
            sold=Coalesce(Sum("booking_items__quantity", filter=ok), 0),
            revenue=Coalesce(Sum(per_type_total, filter=ok), Value(Decimal("0")), output_field=money),
        )
        .order_by("id")
    )
    return {
        "event_id": event.id,
        "title": event.title,
        "tickets_sold": totals["tickets_sold"],
        "revenue": totals["revenue"],
        "per_ticket_type": [
            {"ticket_type_id": t.id, "name": t.name, "sold": t.sold,
             "revenue": t.revenue, "remaining": t.available}
            for t in per_type
        ],
    }
