from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from accounts.models import User
from api.models import ApiToken
from api.permissions import HasIngestScope


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"username": request.user.username})


class IngestProtectedView(APIView):
    permission_classes = [HasIngestScope]

    def post(self, request):
        return Response({"status": "accepted"})


class ApiHealthTests(TestCase):
    def test_health_endpoint_returns_json(self):
        response = self.client.get(reverse("api-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"status": "ok"})


class BearerTokenAuthenticationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email="api-user@example.com",
            username="api-user",
            password="password",
        )
        self.token, self.raw_token = ApiToken.create_token(
            user=self.user,
            name="CI",
            scopes=[ApiToken.READ_SCOPE],
        )

    def test_missing_token_is_rejected(self):
        request = self.factory.get("/protected/")

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_invalid_token_is_rejected(self):
        request = self.factory.get("/protected/", HTTP_AUTHORIZATION="Bearer invalid")

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_malformed_token_header_is_rejected(self):
        request = self.factory.get("/protected/", HTTP_AUTHORIZATION=self.raw_token)

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_inactive_token_is_rejected(self):
        self.token.is_active = False
        self.token.save(update_fields=["is_active", "updated_at"])
        request = self.factory.get("/protected/", HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_valid_token_authenticates_request(self):
        request = self.factory.get("/protected/", HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"username": "api-user"})
        self.token.refresh_from_db()
        self.assertIsNotNone(self.token.last_used_at)

    def test_scope_permission_rejects_missing_scope(self):
        request = self.factory.post("/ingest/", {}, format="json", HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")

        response = IngestProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 403)


class ApiTokenCommandTests(TestCase):
    def test_create_api_token_command_prints_raw_token_once(self):
        user = User.objects.create_user(
            email="runner@example.com",
            username="runner",
            password="password",
        )
        stdout = StringIO()

        call_command(
            "create_api_token",
            user=user.username,
            name="runner-token",
            scopes="read,ingest",
            stdout=stdout,
        )

        token = ApiToken.objects.get(user=user, name="runner-token")
        output = stdout.getvalue()
        raw_token = output.strip().splitlines()[-1]

        self.assertTrue(raw_token.startswith("st_"))
        self.assertEqual(token.scopes, [ApiToken.INGEST_SCOPE, ApiToken.READ_SCOPE])
        self.assertEqual(token.token_hash, ApiToken.hash_token(raw_token))
        self.assertNotEqual(token.token_hash, raw_token)
