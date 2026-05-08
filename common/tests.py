import hashlib

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from common.choices import ResultStatus
from common.utils import calculate_pass_rate, format_percentage, normalize_signature
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


class CalculatePassRateTests(TestCase):
    """Unit tests for common.utils.calculate_pass_rate."""

    def test_full_pass(self):
        self.assertEqual(calculate_pass_rate(100, 100), 100.0)

    def test_partial_pass(self):
        self.assertEqual(calculate_pass_rate(75, 100), 75.0)

    def test_zero_pass(self):
        self.assertEqual(calculate_pass_rate(0, 100), 0.0)

    def test_zero_total_returns_zero(self):
        self.assertEqual(calculate_pass_rate(50, 0), 0.0)

    def test_zero_pass_and_zero_total(self):
        self.assertEqual(calculate_pass_rate(0, 0), 0.0)

    def test_rounding_to_two_decimals(self):
        # 1/3 = 33.333... should round to 33.33
        self.assertEqual(calculate_pass_rate(1, 3), 33.33)

    def test_rounding_up(self):
        # 2/3 = 66.666... should round to 66.67
        self.assertEqual(calculate_pass_rate(2, 3), 66.67)

    def test_returns_float(self):
        result = calculate_pass_rate(50, 100)
        self.assertIsInstance(result, float)


class NormalizeSignatureTests(TestCase):
    """Unit tests for common.utils.normalize_signature."""

    def test_lowercases_text(self):
        self.assertEqual(normalize_signature("DATA MISMATCH"), "data mismatch")

    def test_collapses_multiple_spaces(self):
        self.assertEqual(normalize_signature("data   mismatch"), "data mismatch")

    def test_strips_leading_trailing_whitespace(self):
        self.assertEqual(normalize_signature("  data mismatch  "), "data mismatch")

    def test_empty_string_returns_empty(self):
        self.assertEqual(normalize_signature(""), "")

    def test_none_returns_empty(self):
        self.assertEqual(normalize_signature(None), "")

    def test_preserves_special_characters(self):
        self.assertEqual(normalize_signature("ERROR: assertion FAILED"), "error: assertion failed")


class FormatPercentageTests(TestCase):
    """Unit tests for common.utils.format_percentage."""

    def test_formats_float(self):
        self.assertEqual(format_percentage(75.5), "75.50%")

    def test_formats_integer(self):
        self.assertEqual(format_percentage(100), "100.00%")

    def test_none_returns_zero_percent(self):
        self.assertEqual(format_percentage(None), "0.00%")

    def test_zero_formats_correctly(self):
        self.assertEqual(format_percentage(0), "0.00%")


class SignatureHashServiceTests(TestCase):
    """Tests for results/services.py signature hashing utilities."""

    def test_normalize_and_hash_produces_sha256(self):
        from results.services import normalize_and_hash_signature

        normalized, sig_hash = normalize_and_hash_signature("DATA  Mismatch")
        self.assertEqual(normalized, "data mismatch")
        self.assertEqual(sig_hash, hashlib.sha256("data mismatch".encode("utf-8")).hexdigest())

    def test_same_input_produces_same_hash(self):
        from results.services import normalize_and_hash_signature

        _, hash1 = normalize_and_hash_signature("Assertion error")
        _, hash2 = normalize_and_hash_signature("assertion   ERROR")
        self.assertEqual(hash1, hash2)

    def test_different_input_produces_different_hash(self):
        from results.services import normalize_and_hash_signature

        _, hash1 = normalize_and_hash_signature("timeout error")
        _, hash2 = normalize_and_hash_signature("data mismatch")
        self.assertNotEqual(hash1, hash2)

    def test_get_or_create_signature_creates_new(self):
        from results.services import get_or_create_signature

        user = User.objects.create_user(email="a@b.com", username="a", password="x")
        project = Project.objects.create(name="P1", owner=user)
        regression = Regression.objects.create(project=project, name="R1")
        run = RegressionRun.objects.create(regression=regression, run_number=1)

        sig, created = get_or_create_signature(run, "Data mismatch", category="design")
        self.assertTrue(created)
        self.assertEqual(sig.signature_title, "Data mismatch")
        self.assertEqual(sig.category, "design")
        self.assertEqual(sig.result_count, 0)

    def test_get_or_create_signature_returns_existing(self):
        from results.services import get_or_create_signature

        user = User.objects.create_user(email="b@b.com", username="b", password="x")
        project = Project.objects.create(name="P2", owner=user)
        regression = Regression.objects.create(project=project, name="R2")
        run = RegressionRun.objects.create(regression=regression, run_number=1)

        sig1, created1 = get_or_create_signature(run, "Data mismatch", category="design")
        sig2, created2 = get_or_create_signature(run, "DATA  MISMATCH", category="config")

        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(sig1.pk, sig2.pk)
        # Original title/category preserved on duplicate
        self.assertEqual(sig2.signature_title, "Data mismatch")
        self.assertEqual(sig2.category, "design")


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
