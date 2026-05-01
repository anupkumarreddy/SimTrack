from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from common.choices import ResultStatus
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


class SimTrackSmokeTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="password123",
            is_staff=True,
            is_superuser=True,
        )
        self.viewer = User.objects.create_user(
            email="viewer@example.com",
            username="viewer",
            password="password123",
        )
        self.project = Project.objects.create(name="AXI VIP", owner=self.staff)
        self.regression = Regression.objects.create(project=self.project, name="AXI Smoke", owner=self.staff)
        self.run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=1,
            total_count=2,
            pass_count=1,
            fail_count=1,
            status="completed",
        )
        self.signature = FailureSignature.objects.create(
            regression_run=self.run,
            signature_title="Data mismatch",
            signature_hash="abc123",
            result_count=1,
        )
        Result.objects.create(
            regression_run=self.run,
            failure_signature=self.signature,
            test_name="test_read",
            status=ResultStatus.FAIL,
        )

    def test_anonymous_users_are_redirected_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_login_dashboard_and_regression_detail_smoke(self):
        self.client.login(username="viewer", password="password123")
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk})).status_code, 200
        )

    def test_viewer_cannot_access_write_views(self):
        self.client.login(username="viewer", password="password123")
        response = self.client.get(reverse("project-create"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_write_views(self):
        self.client.login(username="admin", password="password123")
        response = self.client.get(reverse("project-create"))
        self.assertEqual(response.status_code, 200)

    def test_run_pass_rate_is_calculated_on_save(self):
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=2,
            total_count=4,
            pass_count=3,
        )
        self.assertEqual(run.pass_rate, 75)

    def test_small_seed_demo_data_command(self):
        call_command("seed_demo_data", "--small", verbosity=0)
        self.assertTrue(Project.objects.exists())
        self.assertTrue(Regression.objects.exists())
        self.assertTrue(RegressionRun.objects.exists())

    def test_create_demo_user_command_creates_read_only_user(self):
        call_command("create_demo_user", username="demo_test", password="demo", verbosity=0)
        user = User.objects.get(username="demo_test")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("demo"))
