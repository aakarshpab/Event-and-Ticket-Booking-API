from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.chat.models import Conversation
from apps.chat.services.context import build_event_context
from apps.chat.services.llm import LLMServiceError
from step1etm.testing import make_event, make_ticket, make_user

# The real AI service is NEVER called in tests: we mock generate_reply.
MOCK = "apps.chat.services.llm.generate_reply"


class ChatTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.client.force_authenticate(self.alice)

    @patch(MOCK, return_value="There is Rock Night in Delhi.")
    def test_chat_creates_conversation_and_saves_messages(self, mock_llm):
        res = self.client.post("/api/v1/chat/", {"message": "What is on in Delhi?"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["reply"], "There is Rock Night in Delhi.")
        conv = Conversation.objects.get(pk=res.data["conversation_id"])
        self.assertEqual(conv.messages.count(), 2)
        mock_llm.assert_called_once()

    @patch(MOCK, return_value="Sure")
    def test_follow_up_sends_history(self, mock_llm):
        first = self.client.post("/api/v1/chat/", {"message": "Hi"}, format="json")
        self.client.post("/api/v1/chat/", {"message": "Again", "conversation_id": first.data["conversation_id"]}, format="json")
        history = mock_llm.call_args.kwargs["history"]
        self.assertEqual([m["role"] for m in history], ["user", "assistant"])

    @patch(MOCK, side_effect=LLMServiceError())
    def test_ai_service_down_returns_standard_error(self, _):
        res = self.client.post("/api/v1/chat/", {"message": "Hi"}, format="json")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.data["error"]["code"], "ai_service_unavailable")
        self.assertEqual(Conversation.objects.count(), 0)

    @patch(MOCK, return_value="ok")
    def test_chat_is_throttled(self, _):
        codes = [self.client.post("/api/v1/chat/", {"message": "Hi"}, format="json").status_code for _ in range(6)]
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[5], 429)

    @patch(MOCK, return_value="ok")
    def test_users_only_see_their_own_conversations(self, _):
        res = self.client.post("/api/v1/chat/", {"message": "Hi"}, format="json")
        cid = res.data["conversation_id"]
        self.assertEqual(self.client.get("/api/v1/chat/conversations/").data["count"], 1)
        self.assertEqual(len(self.client.get(f"/api/v1/chat/conversations/{cid}/").data["messages"]), 2)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get("/api/v1/chat/conversations/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/v1/chat/conversations/{cid}/").status_code, 404)
        res = self.client.post("/api/v1/chat/", {"message": "Hi", "conversation_id": cid}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_context_contains_real_event_data(self):
        org = make_user("org", "organizer")
        event = make_event(org, city="Delhi", title="Rock Night")
        make_ticket(event, name="VIP", price="900", total=3)
        text = build_event_context("What is on in Delhi under 1000 rupees?")
        self.assertIn("Rock Night", text)
        self.assertIn("VIP Rs900 (3 left)", text)
        self.assertIn("No matching", build_event_context("events in Paris under 10"))
