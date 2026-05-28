from django.test import TestCase
from django.urls import reverse


class ApiHealthTests(TestCase):
    def test_health_endpoint_returns_json(self):
        response = self.client.get(reverse("api-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"status": "ok"})
