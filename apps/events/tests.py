from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.events.models import Event
from step1etm.testing import make_event, make_ticket, make_user, make_venue


class EventTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.organizer = make_user("org", "organizer")
        self.other_org = make_user("org2", "organizer")
        self.attendee = make_user("alice")

    def payload(self, **extra):
        start = timezone.now() + timedelta(days=5)
        data = {
            "title": "Tech Meetup", "description": "Talks", "category": "tech",
            "venue_id": make_venue("Mumbai").id,
            "start_time": start.isoformat(), "end_time": (start + timedelta(hours=2)).isoformat(),
        }
        data.update(extra)
        return data

    def test_organizer_creates_event_and_gets_nested_venue(self):
        self.client.force_authenticate(self.organizer)
        res = self.client.post("/api/v1/events/", self.payload(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["venue"]["city"], "Mumbai")  # nested on read
        self.assertEqual(res.data["organizer"], "org")

    def test_attendee_cannot_create_event(self):
        self.client.force_authenticate(self.attendee)
        res = self.client.post("/api/v1/events/", self.payload(), format="json")
        self.assertEqual(res.status_code, 403)

    def test_end_time_must_be_after_start_time(self):
        self.client.force_authenticate(self.organizer)
        start = timezone.now() + timedelta(days=5)
        res = self.client.post("/api/v1/events/", self.payload(
            start_time=start.isoformat(), end_time=(start - timedelta(hours=1)).isoformat()), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error"]["code"], "validation_error")

    def test_event_in_the_past_rejected(self):
        self.client.force_authenticate(self.organizer)
        past = timezone.now() - timedelta(days=2)
        res = self.client.post("/api/v1/events/", self.payload(
            start_time=past.isoformat(), end_time=(past + timedelta(hours=1)).isoformat()), format="json")
        self.assertEqual(res.status_code, 400)

    def test_only_owner_can_edit_event(self):
        event = make_event(self.organizer)
        self.client.force_authenticate(self.other_org)
        self.assertEqual(self.client.patch(f"/api/v1/events/{event.id}/", {"title": "Hacked"}).status_code, 403)
        self.client.force_authenticate(self.organizer)
        res = self.client.patch(f"/api/v1/events/{event.id}/", {"title": "New title"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "New title")

    def test_only_owner_can_delete_event(self):
        event = make_event(self.organizer)
        self.client.force_authenticate(self.other_org)
        self.assertEqual(self.client.delete(f"/api/v1/events/{event.id}/").status_code, 403)
        self.client.force_authenticate(self.organizer)
        self.assertEqual(self.client.delete(f"/api/v1/events/{event.id}/").status_code, 204)

    def test_attendee_can_read_events(self):
        make_event(self.organizer)
        self.client.force_authenticate(self.attendee)
        res = self.client.get("/api/v1/events/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)

    def test_unpublished_event_hidden_from_attendees(self):
        event = make_event(self.organizer)
        Event.objects.filter(pk=event.pk).update(is_published=False)
        self.client.force_authenticate(self.attendee)
        self.assertEqual(self.client.get("/api/v1/events/").data["count"], 0)

    def test_negative_ticket_price_rejected(self):
        event = make_event(self.organizer)
        self.client.force_authenticate(self.organizer)
        res = self.client.post("/api/v1/ticket-types/", {
            "event": event.id, "name": "General", "price": "-5", "quantity_total": 10}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cannot_add_ticket_type_to_someone_elses_event(self):
        event = make_event(self.organizer)
        self.client.force_authenticate(self.other_org)
        res = self.client.post("/api/v1/ticket-types/", {
            "event": event.id, "name": "General", "price": "10", "quantity_total": 10}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_search_filter_and_ordering(self):
        e1 = make_event(self.organizer, city="Delhi", title="Jazz Night", category="music", days_from_now=3)
        e2 = make_event(self.organizer, city="Kolkata", title="Code Camp", category="tech", days_from_now=1)
        make_ticket(e1, price="300")
        make_ticket(e2, price="1500")
        self.client.force_authenticate(self.attendee)
        get = lambda q: [e["title"] for e in self.client.get(f"/api/v1/events/{q}").data["results"]]
        self.assertEqual(get("?search=jazz"), ["Jazz Night"])
        self.assertEqual(get("?search=kolkata"), ["Code Camp"])
        self.assertEqual(get("?category=tech"), ["Code Camp"])
        self.assertEqual(get("?max_price=1000"), ["Jazz Night"])
        self.assertEqual(get("?min_price=1000"), ["Code Camp"])
        self.assertEqual(get("?city=delhi"), ["Jazz Night"])
        self.assertEqual(get("?ordering=-start_time"), ["Jazz Night", "Code Camp"])

    def test_swagger_schema_is_available(self):
        self.client.force_authenticate(self.attendee)
        self.assertEqual(self.client.get("/api/v1/schema/").status_code, 200)
