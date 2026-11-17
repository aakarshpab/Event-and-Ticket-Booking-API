"""Small helpers used by the tests of every app."""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Event, TicketType, Venue


def make_user(username, role="attendee", password="StrongPass123!"):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=password, role=role
    )


def make_venue(city="Delhi"):
    return Venue.objects.create(name=f"{city} Hall", address="1 Main Road", city=city, capacity=500)


def make_event(organizer, days_from_now=10, city="Delhi", title="Rock Night", category="music"):
    start = timezone.now() + timedelta(days=days_from_now)
    return Event.objects.create(
        title=title,
        description="A great show",
        category=category,
        venue=make_venue(city),
        start_time=start,
        end_time=start + timedelta(hours=3),
        organizer=organizer,
    )


def make_ticket(event, name="General", price="500.00", total=10):
    return TicketType.objects.create(
        event=event, name=name, price=Decimal(price), quantity_total=total
    )
