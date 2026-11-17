"""Fetch real events from the database and turn them into text for the prompt."""
import re
from datetime import timedelta

from django.utils import timezone

from apps.events.models import Event, Venue

EVENT_ID_RE = re.compile(r"event\s*#?\s*(\d+)", re.IGNORECASE)
PRICE_RE = re.compile(r"(?:under|below|less than|within|upto|up to)\s*(?:rs\.?|inr|₹)?\s*(\d+)", re.IGNORECASE)


def _rs(price):
    """Decimal('900.00') -> '900', Decimal('99.50') -> '99.50'"""
    return str(int(price)) if price == price.to_integral_value() else str(price)


def build_event_context(message, limit=8):
    text = message.lower()
    events = (
        Event.objects.filter(is_published=True, start_time__gte=timezone.now())
        .select_related("venue")
        .prefetch_related("ticket_types")
    )

    match = EVENT_ID_RE.search(message)
    if match:
        events = events.filter(pk=int(match.group(1)))
    else:
        for city in Venue.objects.values_list("city", flat=True).distinct():
            if city.lower() in text:
                events = events.filter(venue__city__iexact=city)
                break
        price = PRICE_RE.search(message)
        if price:
            events = events.filter(ticket_types__price__lte=int(price.group(1))).distinct()
        if "weekend" in text:
            # Django week_day: Sunday=1 ... Saturday=7
            events = events.filter(
                start_time__lte=timezone.now() + timedelta(days=7), start_time__week_day__in=[1, 7]
            )

    lines = []
    for e in events.order_by("start_time")[:limit]:
        tickets = ", ".join(
            f"{t.name} Rs{_rs(t.price)} ({t.available} left)" if t.available else f"{t.name} Rs{_rs(t.price)} (sold out)"
            for t in e.ticket_types.all()
        ) or "no ticket types yet"
        when = timezone.localtime(e.start_time).strftime("%a %d %b %Y, %I:%M %p")
        lines.append(f"- Event ID {e.id}: {e.title} [{e.category}] at {e.venue.name}, {e.venue.city}, {when}. Tickets: {tickets}")
    return "\n".join(lines) or "No matching upcoming events were found."
