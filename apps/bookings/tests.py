from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.events.models import TicketType
from step1etm.testing import make_event, make_ticket, make_user


class BookingTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.organizer = make_user("org", "organizer")
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.event = make_event(self.organizer)
        self.ticket = make_ticket(self.event, total=5)
        self.book_url = f"/api/v1/events/{self.event.id}/book/"

    def book(self, user, qty=1, ticket=None):
        self.client.force_authenticate(user)
        ticket = ticket or self.ticket
        return self.client.post(self.book_url, {"items": [{"ticket_type": ticket.id, "quantity": qty}]}, format="json")

    def test_successful_booking_updates_inventory(self):
        res = self.book(self.alice, qty=2)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Decimal(res.data["total_amount"]), Decimal("1000.00"))
        self.assertEqual(res.data["payment_status"], "paid")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.quantity_sold, 2)

    def test_cannot_book_more_than_available(self):
        res = self.book(self.alice, qty=6)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error"]["code"], "booking_error")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.quantity_sold, 0)

    def test_overbooking_last_ticket(self):
        last = make_ticket(self.event, name="VIP", price="2000.00", total=1)
        self.assertEqual(self.book(self.alice, ticket=last).status_code, 201)
        res = self.book(self.bob, ticket=last)  # second buyer must fail
        self.assertEqual(res.status_code, 400)
        last.refresh_from_db()
        self.assertEqual(last.quantity_sold, 1)
        self.assertEqual(Booking.objects.filter(event=self.event).count(), 1)

    def test_price_snapshot_not_changed_by_later_price_update(self):
        res = self.book(self.alice, qty=1)
        self.ticket.price = Decimal("999.00")
        self.ticket.save()
        self.client.force_authenticate(self.alice)
        res = self.client.get(f"/api/v1/bookings/{res.data['id']}/")
        self.assertEqual(Decimal(res.data["items"][0]["unit_price"]), Decimal("500.00"))

    def test_cancel_restores_inventory(self):
        res = self.book(self.alice, qty=3)
        res = self.client.post(f"/api/v1/bookings/{res.data['id']}/cancel/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "cancelled")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.quantity_sold, 0)

    def test_cannot_cancel_within_24_hours(self):
        res = self.book(self.alice)
        self.event.start_time = timezone.now() + timedelta(hours=5)
        self.event.end_time = self.event.start_time + timedelta(hours=2)
        self.event.save()
        res = self.client.post(f"/api/v1/bookings/{res.data['id']}/cancel/")
        self.assertEqual(res.status_code, 400)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.quantity_sold, 1)

    def test_cannot_cancel_twice(self):
        res = self.book(self.alice)
        url = f"/api/v1/bookings/{res.data['id']}/cancel/"
        self.client.post(url)
        self.assertEqual(self.client.post(url).status_code, 400)

    def test_user_cannot_see_other_users_booking(self):
        res = self.book(self.alice)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(f"/api/v1/bookings/{res.data['id']}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/bookings/").data["count"], 0)

    def test_admin_can_see_any_booking(self):
        res = self.book(self.alice)
        admin = make_user("boss", "admin")
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get(f"/api/v1/bookings/{res.data['id']}/").status_code, 200)

    def test_organizer_cannot_book(self):
        self.assertEqual(self.book(self.organizer).status_code, 403)

    def test_anonymous_cannot_book(self):
        self.client.force_authenticate(None)
        res = self.client.post(self.book_url, {"items": [{"ticket_type": self.ticket.id, "quantity": 1}]}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_stats_for_organizer(self):
        self.book(self.alice, qty=2)
        self.book(self.bob, qty=1)
        self.client.force_authenticate(self.organizer)
        res = self.client.get(f"/api/v1/events/{self.event.id}/stats/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["tickets_sold"], 3)
        self.assertEqual(Decimal(res.data["revenue"]), Decimal("1500.00"))
        self.assertEqual(res.data["per_ticket_type"][0]["sold"], 3)

    def test_stats_forbidden_for_attendee_and_other_organizer(self):
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get(f"/api/v1/events/{self.event.id}/stats/").status_code, 403)
        self.client.force_authenticate(make_user("org2", "organizer"))
        self.assertEqual(self.client.get(f"/api/v1/events/{self.event.id}/stats/").status_code, 403)

    def test_cancelled_bookings_not_counted_in_stats(self):
        res = self.book(self.alice, qty=2)
        self.client.post(f"/api/v1/bookings/{res.data['id']}/cancel/")
        self.client.force_authenticate(self.organizer)
        res = self.client.get(f"/api/v1/events/{self.event.id}/stats/")
        self.assertEqual(res.data["tickets_sold"], 0)
