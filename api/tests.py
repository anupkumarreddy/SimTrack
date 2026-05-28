from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from accounts.models import User
from api.models import ApiToken
from api.permissions import HasIngestScope
from common.choices import ResultStatus, RunStatus, TriggerType
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


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


class ApiEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tool@example.com",
            username="tool",
            password="password",
        )
        self.read_token, self.raw_read_token = ApiToken.create_token(
            user=self.user,
            name="reader",
            scopes=[ApiToken.READ_SCOPE],
        )
        self.ingest_token, self.raw_ingest_token = ApiToken.create_token(
            user=self.user,
            name="ingester",
            scopes=[ApiToken.INGEST_SCOPE],
        )
        self.write_token, self.raw_write_token = ApiToken.create_token(
            user=self.user,
            name="writer",
            scopes=[ApiToken.WRITE_SCOPE],
        )
        self.full_token, self.raw_full_token = ApiToken.create_token(
            user=self.user,
            name="full",
            scopes=[ApiToken.READ_SCOPE, ApiToken.WRITE_SCOPE, ApiToken.INGEST_SCOPE],
        )
        self.client = APIClient()

    def authorize(self, raw_token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")

    def create_run_data(self):
        project = Project.objects.create(name="Core", slug="core")
        regression = Regression.objects.create(project=project, name="nightly")
        run = RegressionRun.objects.create(
            regression=regression,
            run_number=1,
            status=RunStatus.COMPLETED,
            trigger_type=TriggerType.API,
            branch_name="main",
            suite_name="smoke",
        )
        Result.objects.create(regression_run=run, test_name="test_pass", status=ResultStatus.PASS)
        Result.objects.create(regression_run=run, test_name="test_fail", status=ResultStatus.FAIL)
        return project, regression, run

    def test_read_endpoint_requires_token(self):
        response = self.client.get(reverse("api-project-list"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"], "authentication_required")
        self.assertEqual(response.data["fields"], {})

    def test_read_endpoint_requires_read_scope(self):
        self.authorize(self.raw_ingest_token)

        response = self.client.get(reverse("api-project-list"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"], "permission_denied")

    def test_create_project_requires_write_scope(self):
        self.authorize(self.raw_read_token)

        response = self.client.post(reverse("api-project-list"), {"name": "Write Blocked"}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"], "permission_denied")

    def test_invalid_token_returns_standard_error_shape(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid")

        response = self.client.get(reverse("api-project-list"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"], "invalid_token")
        self.assertIn("message", response.data)
        self.assertEqual(response.data["fields"], {})

    def test_validation_error_returns_standard_error_shape(self):
        self.authorize(self.raw_write_token)

        response = self.client.post(reverse("api-project-list"), {"status": "not-valid"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "validation_error")
        self.assertIn("name", response.data["fields"])

    def test_not_found_returns_standard_error_shape(self):
        self.authorize(self.raw_read_token)

        response = self.client.get(reverse("api-project-detail", kwargs={"pk": 99999}))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "not_found")

    def test_method_not_allowed_returns_standard_error_shape(self):
        project, _, _ = self.create_run_data()
        self.authorize(self.raw_write_token)

        response = self.client.delete(reverse("api-project-detail", kwargs={"pk": project.pk}))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["error"], "method_not_allowed")

    def test_schema_requires_read_scope(self):
        self.authorize(self.raw_ingest_token)

        response = self.client.get(reverse("api-schema"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"], "permission_denied")

    def test_schema_returns_openapi_document(self):
        self.authorize(self.raw_read_token)

        response = self.client.get(reverse("api-schema"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["info"]["title"], "SimTrack API")

    def test_write_token_can_create_and_patch_project(self):
        self.authorize(self.raw_write_token)

        create_response = self.client.post(
            reverse("api-project-list"),
            {
                "name": "API Project",
                "slug": "api-project",
                "description": "Created through API",
                "status": "active",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        project = Project.objects.get(slug="api-project")
        self.assertEqual(project.description, "Created through API")

        patch_response = self.client.patch(
            reverse("api-project-detail", kwargs={"pk": project.pk}),
            {"description": "Updated through API"},
            format="json",
        )

        self.assertEqual(patch_response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.description, "Updated through API")

    def test_write_token_can_create_and_patch_regression(self):
        project = Project.objects.create(name="Core", slug="core")
        self.authorize(self.raw_write_token)

        create_response = self.client.post(
            reverse("api-regression-list"),
            {
                "project": project.pk,
                "name": "api-nightly",
                "description": "API regression",
                "default_branch_name": "main",
                "default_suite_name": "smoke",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        regression = Regression.objects.get(project=project, name="api-nightly")

        patch_response = self.client.patch(
            reverse("api-regression-detail", kwargs={"pk": regression.pk}),
            {"default_config_name": "fast"},
            format="json",
        )

        self.assertEqual(patch_response.status_code, 200)
        regression.refresh_from_db()
        self.assertEqual(regression.default_config_name, "fast")

    def test_write_token_can_create_run_and_server_managed_fields_are_ignored(self):
        project = Project.objects.create(name="Core", slug="core")
        regression = Regression.objects.create(project=project, name="nightly")
        self.authorize(self.raw_write_token)

        response = self.client.post(
            reverse("api-run-list"),
            {
                "regression": regression.pk,
                "run_name": "api-run",
                "status": "completed",
                "trigger_type": "api",
                "total_count": 99,
                "pass_count": 99,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        run = RegressionRun.objects.get(regression=regression, run_name="api-run")
        self.assertEqual(run.run_number, 1)
        self.assertEqual(run.triggered_by, self.user)
        self.assertEqual(run.total_count, 0)
        self.assertEqual(run.pass_count, 0)

    def test_write_token_can_patch_run(self):
        _, _, run = self.create_run_data()
        self.authorize(self.raw_write_token)

        response = self.client.patch(
            reverse("api-run-detail", kwargs={"pk": run.pk}),
            {"status": "aborted", "notes": "Stopped by API"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.status, "aborted")
        self.assertEqual(run.notes, "Stopped by API")

    def test_put_and_delete_are_not_enabled_for_core_write_endpoints(self):
        project, _, _ = self.create_run_data()
        self.authorize(self.raw_write_token)

        put_response = self.client.put(
            reverse("api-project-detail", kwargs={"pk": project.pk}),
            {"name": "Replacement"},
            format="json",
        )
        delete_response = self.client.delete(reverse("api-project-detail", kwargs={"pk": project.pk}))

        self.assertEqual(put_response.status_code, 405)
        self.assertEqual(delete_response.status_code, 405)

    def test_project_list_returns_paginated_results(self):
        project, _, _ = self.create_run_data()
        self.authorize(self.raw_read_token)

        response = self.client.get(reverse("api-project-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], project.pk)

    def test_run_list_filters_by_project_status_branch_and_suite(self):
        project, _, run = self.create_run_data()
        self.authorize(self.raw_read_token)

        response = self.client.get(
            reverse("api-run-list"),
            {
                "project": project.pk,
                "status": RunStatus.COMPLETED,
                "branch": "main",
                "suite": "smoke",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], run.pk)

    def test_result_detail_returns_expected_result(self):
        _, _, run = self.create_run_data()
        result = run.results.get(test_name="test_fail")
        self.authorize(self.raw_read_token)

        response = self.client.get(reverse("api-result-detail", kwargs={"pk": result.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["test_name"], "test_fail")
        self.assertEqual(response.data["regression_run"], run.pk)

    def test_ingest_requires_ingest_scope(self):
        self.authorize(self.raw_read_token)

        response = self.client.post(reverse("api-ingest-run"), {}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_ingest_run_creates_models_results_and_counters(self):
        self.authorize(self.raw_full_token)
        payload = {
            "project": {
                "slug": "chip-top",
                "name": "Chip Top",
            },
            "regression": {
                "name": "nightly-smoke",
                "branch_name": "main",
                "suite_name": "smoke",
                "config_name": "default",
            },
            "run": {
                "run_number": 1042,
                "run_name": "nightly-smoke-2026-05-28",
                "status": "completed",
                "trigger_type": "ci",
                "build_id": "build-123",
                "git_commit": "abc123",
                "start_time": "2026-05-28T01:00:00Z",
                "end_time": "2026-05-28T01:12:30Z",
                "metadata": {
                    "ci_url": "https://ci.example.com/build/123",
                },
            },
            "results": [
                {
                    "test_name": "test_reset_sequence",
                    "status": "pass",
                    "seed": "1001",
                    "duration_seconds": "12.4",
                    "machine_name": "runner-01",
                },
                {
                    "test_name": "test_axi_timeout",
                    "status": "fail",
                    "seed": "1002",
                    "duration_seconds": "35.8",
                    "machine_name": "runner-02",
                    "error_message": "AXI timeout waiting for response",
                    "failure_signature": {
                        "title": "AXI timeout waiting for response",
                        "category": "timeout",
                        "is_infra_issue": False,
                        "is_known_issue": False,
                    },
                },
            ],
        }

        response = self.client.post(reverse("api-ingest-run"), payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created"], {"project": True, "regression": True, "run": True})
        self.assertEqual(response.data["result_count"], 2)
        run = RegressionRun.objects.get(regression__name="nightly-smoke", run_number=1042)
        self.assertEqual(run.triggered_by, self.user)
        self.assertEqual(run.total_count, 2)
        self.assertEqual(run.pass_count, 1)
        self.assertEqual(run.fail_count, 1)
        self.assertEqual(str(run.pass_rate), "50.00")
        signature = FailureSignature.objects.get(regression_run=run)
        self.assertEqual(signature.result_count, 1)
        self.assertEqual(run.results.filter(failure_signature=signature).count(), 1)

    def test_ingest_run_replaces_existing_results_for_same_run(self):
        self.authorize(self.raw_full_token)
        payload = {
            "project": {"slug": "chip-top", "name": "Chip Top"},
            "regression": {"name": "nightly-smoke"},
            "run": {"run_number": 1, "status": "completed", "trigger_type": "api"},
            "results": [
                {"test_name": "test_a", "status": "pass"},
                {"test_name": "test_b", "status": "fail", "failure_signature": {"title": "first fail"}},
            ],
        }

        first_response = self.client.post(reverse("api-ingest-run"), payload, format="json")
        second_response = self.client.post(reverse("api-ingest-run"), payload, format="json")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        run = RegressionRun.objects.get(regression__name="nightly-smoke", run_number=1)
        self.assertEqual(run.results.count(), 2)
        self.assertEqual(run.failure_signatures.count(), 1)
        self.assertEqual(run.total_count, 2)
