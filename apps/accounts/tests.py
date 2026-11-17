from django.core.cache import cache
from rest_framework.test import APITestCase
from step1etm.testing import make_user


class AccountsTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttle counters

    def test_register_attendee_returns_token(self):
        data = {"username": "ravi", "email": "ravi@example.com", "password": "StrongPass123!", "role": "attendee"}
        res = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(res.status_code, 201)
        self.assertIn("token", res.data)
        self.assertEqual(res.data["user"]["role"], "attendee")

    def test_cannot_register_as_admin(self):
        data = {"username": "evil", "email": "e@example.com", "password": "StrongPass123!", "role": "admin"}
        res = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error"]["code"], "validation_error")

    def test_login_returns_token(self):
        make_user("sita")
        res = self.client.post("/api/v1/auth/login/", {"username": "sita", "password": "StrongPass123!"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("token", res.data)

    def test_me_requires_authentication(self):
        res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, 401)
        self.assertIn("error", res.data)
