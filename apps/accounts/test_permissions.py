"""Role-based access control tests: Admin vs Organizer vs Attendee."""
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from step1etm.testing import make_event, make_ticket, make_user, make_venue


class RolePermissionTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user("boss", "admin")
        self.org = make_user("org", "organizer")
        self.org2 = make_user("org2", "organizer")
        self.att = make_user("att", "attendee")
        self.event = make_event(self.org)
        self.ticket = make_ticket(self.event, total=5)

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def event_payload(self):
        start = timezone.now() + timedelta(days=4)
        return {"title": "New", "category": "arts", "venue_id": make_venue("Pune").id,
                "start_time": start.isoformat(), "end_time": (start + timedelta(hours=2)).isoformat()}

    # ---- anonymous users ----
    def test_anonymous_gets_401_everywhere(self):
        for url in ["/api/v1/events/", "/api/v1/venues/", "/api/v1/bookings/", "/api/v1/chat/conversations/"]:
            self.assertEqual(self.client.get(url).status_code, 401, url)

    # ---- who can create events ----
    def test_create_event_by_role(self):
        expected = {self.admin: 201, self.org: 201, self.att: 403}
        for user, code in expected.items():
            res = self.as_user(user).post("/api/v1/events/", self.event_payload(), format="json")
            self.assertEqual(res.status_code, code, user.username)

    def test_create_venue_by_role(self):
        data = {"name": "Arena", "address": "Road 1", "city": "Goa", "capacity": 100}
        self.assertEqual(self.as_user(self.att).post("/api/v1/venues/", data).status_code, 403)
        self.assertEqual(self.as_user(self.org).post("/api/v1/venues/", data).status_code, 201)

    # ---- editing / deleting ----
    def test_edit_event_by_role(self):
        url = f"/api/v1/events/{self.event.id}/"
        self.assertEqual(self.as_user(self.att).patch(url, {"title": "x"}).status_code, 403)
        self.assertEqual(self.as_user(self.org2).patch(url, {"title": "x"}).status_code, 403)
        self.assertEqual(self.as_user(self.org).patch(url, {"title": "mine"}).status_code, 200)
        self.assertEqual(self.as_user(self.admin).patch(url, {"title": "admin"}).status_code, 200)

    def test_delete_event_by_role(self):
        url = f"/api/v1/events/{self.event.id}/"
        self.assertEqual(self.as_user(self.att).delete(url).status_code, 403)
        self.assertEqual(self.as_user(self.org2).delete(url).status_code, 403)
        self.assertEqual(self.as_user(self.admin).delete(url).status_code, 204)

    # ---- attendee-only action ----
    def test_only_attendee_can_book(self):
        body = {"items": [{"ticket_type": self.ticket.id, "quantity": 1}]}
        url = f"/api/v1/events/{self.event.id}/book/"
        self.assertEqual(self.as_user(self.org).post(url, body, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.admin).post(url, body, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.att).post(url, body, format="json").status_code, 201)

    # ---- organizer-only stats ----
    def test_stats_access_by_role(self):
        url = f"/api/v1/events/{self.event.id}/stats/"
        self.assertEqual(self.as_user(self.att).get(url).status_code, 403)
        self.assertEqual(self.as_user(self.org2).get(url).status_code, 403)
        self.assertEqual(self.as_user(self.org).get(url).status_code, 200)
        self.assertEqual(self.as_user(self.admin).get(url).status_code, 200)

    # ---- ticket types ----
    def test_ticket_type_write_access(self):
        body = {"event": self.event.id, "name": "VIP", "price": "900", "quantity_total": 5}
        self.assertEqual(self.as_user(self.att).post("/api/v1/ticket-types/", body).status_code, 403)
        self.assertEqual(self.as_user(self.org2).post("/api/v1/ticket-types/", body).status_code, 400)
        self.assertEqual(self.as_user(self.org).post("/api/v1/ticket-types/", body).status_code, 201)

    # ---- bookings visibility ----
    def test_booking_visibility_by_role(self):
        body = {"items": [{"ticket_type": self.ticket.id, "quantity": 1}]}
        res = self.as_user(self.att).post(f"/api/v1/events/{self.event.id}/book/", body, format="json")
        url = f"/api/v1/bookings/{res.data['id']}/"
        self.assertEqual(self.as_user(self.att).get(url).status_code, 200)
        self.assertEqual(self.as_user(self.admin).get(url).status_code, 200)
        self.assertEqual(self.as_user(self.org).get(url).status_code, 404)
        self.assertEqual(self.as_user(self.make_other()).get(url).status_code, 404)

    def make_other(self):
        return make_user("other")

    # ---- error format ----
    def test_forbidden_uses_standard_error_format(self):
        res = self.as_user(self.att).post("/api/v1/events/", self.event_payload(), format="json")
        self.assertEqual(res.data["error"]["status_code"], 403)
        self.assertEqual(res.data["error"]["code"], "permission_denied")
