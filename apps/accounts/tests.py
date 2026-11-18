from django.core.cache import cache
from rest_framework.test import APITestCase

from step1etm.testing import make_user


class AccountsTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttle counters

    def test_register_attendee_returns_jwt_tokens(self):
        data = {"username": "ravi", "email": "ravi@example.com", "password": "StrongPass123!", "role": "attendee"}
        res = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(res.status_code, 201)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["role"], "attendee")

    def test_cannot_register_as_admin(self):
        data = {"username": "evil", "email": "e@example.com", "password": "StrongPass123!", "role": "admin"}
        res = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error"]["code"], "validation_error")

    def test_login_returns_access_refresh_and_user(self):
        make_user("sita")
        res = self.client.post("/api/v1/auth/login/", {"username": "sita", "password": "StrongPass123!"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["username"], "sita")

    def test_wrong_password_rejected(self):
        make_user("sita")
        res = self.client.post("/api/v1/auth/login/", {"username": "sita", "password": "wrong"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("error", res.data)

    def test_access_token_works_in_bearer_header(self):
        make_user("sita")
        login = self.client.post("/api/v1/auth/login/", {"username": "sita", "password": "StrongPass123!"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["username"], "sita")

    def test_refresh_token_gives_new_access_token(self):
        make_user("sita")
        login = self.client.post("/api/v1/auth/login/", {"username": "sita", "password": "StrongPass123!"})
        res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": login.data["refresh"]})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_fake_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, 401)

    def test_me_requires_authentication(self):
        res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, 401)
        self.assertIn("error", res.data)
