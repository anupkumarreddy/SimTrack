from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from regressions.models import Regression, RegressionRun
from regressions.services import get_next_run_number


class RegressionRunDurationDisplayTests(TestCase):
    """Tests for RegressionRun.duration_display property."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(name="Test Project")
        cls.regression = Regression.objects.create(
            project=cls.project,
            name="Test Regression",
        )

    def test_no_start_or_end_returns_dash(self):
        """When neither start_time nor end_time is set, returns '-'."""
        run = RegressionRun.objects.create(regression=self.regression, run_number=1)
        self.assertEqual(run.duration_display(), "-")

    def test_only_start_time_returns_dash(self):
        """When only start_time is set (no end_time), returns '-'."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=2,
            start_time=timezone.now(),
        )
        self.assertEqual(run.duration_display(), "-")

    def test_only_end_time_returns_dash(self):
        """When only end_time is set (no start_time), returns '-'."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=3,
            end_time=timezone.now(),
        )
        self.assertEqual(run.duration_display(), "-")

    def test_zero_seconds(self):
        """When start_time equals end_time, returns '00:00:00'."""
        now = timezone.now()
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=4,
            start_time=now,
            end_time=now,
        )
        self.assertEqual(run.duration_display(), "00:00:00")

    def test_exact_seconds(self):
        """Duration of exactly 3661 seconds formats as '01:01:01'."""
        start = timezone.now()
        end = start + timedelta(seconds=3661)  # 1h 1m 1s
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=5,
            start_time=start,
            end_time=end,
        )
        self.assertEqual(run.duration_display(), "01:01:01")

    def test_minutes_and_seconds(self):
        """Duration of 23 minutes 45 seconds formats as '00:23:45'."""
        start = timezone.now()
        end = start + timedelta(minutes=23, seconds=45)
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=6,
            start_time=start,
            end_time=end,
        )
        self.assertEqual(run.duration_display(), "00:23:45")

    def test_one_hour_exact(self):
        """Duration of exactly 1 hour formats as '01:00:00'."""
        start = timezone.now()
        end = start + timedelta(hours=1)
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=7,
            start_time=start,
            end_time=end,
        )
        self.assertEqual(run.duration_display(), "01:00:00")

    def test_long_duration_exceeds_24h(self):
        """Duration exceeding 24 hours shows total hours (e.g., '25:00:00')."""
        start = timezone.now()
        end = start + timedelta(hours=25)
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=8,
            start_time=start,
            end_time=end,
        )
        self.assertEqual(run.duration_display(), "25:00:00")

    def test_very_long_duration(self):
        """Duration of 100 hours formats as '100:00:00'."""
        start = timezone.now()
        end = start + timedelta(hours=100, minutes=15, seconds=30)
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=9,
            start_time=start,
            end_time=end,
        )
        self.assertEqual(run.duration_display(), "100:15:30")

    def test_fractional_seconds_truncated(self):
        """Fractional seconds are truncated (not rounded)."""
        start = timezone.now()
        end = start + timedelta(seconds=90, microseconds=999999)  # 1m 30.999999s
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=10,
            start_time=start,
            end_time=end,
        )
        # int() truncates, so 90.999... → 90 → "00:01:30"
        self.assertEqual(run.duration_display(), "00:01:30")


class RegressionRunPassRateTests(TestCase):
    """Tests for RegressionRun pass_rate calculation on save."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(name="Test Project")
        cls.regression = Regression.objects.create(
            project=cls.project,
            name="Test Regression",
        )

    def test_no_results_pass_rate_zero(self):
        """Run with total_count=0 has pass_rate=0.00."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=1,
            total_count=0,
            pass_count=0,
        )
        self.assertEqual(run.pass_rate, 0)

    def test_all_pass(self):
        """Run where all tests pass has pass_rate=100.00."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=2,
            total_count=50,
            pass_count=50,
        )
        self.assertEqual(run.pass_rate, 100.0)

    def test_all_fail(self):
        """Run where all tests fail has pass_rate=0.00."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=3,
            total_count=50,
            pass_count=0,
            fail_count=50,
        )
        self.assertEqual(run.pass_rate, 0.0)

    def test_mixed_results(self):
        """Run with mixed results calculates correct percentage."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=4,
            total_count=200,
            pass_count=150,
            fail_count=30,
            timeout_count=10,
            skip_count=10,
        )
        self.assertEqual(run.pass_rate, 75.0)

    def test_recalculates_on_update(self):
        """Updating counts and re-saving recalculates pass_rate."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=5,
            total_count=10,
            pass_count=5,
        )
        self.assertEqual(run.pass_rate, 50.0)

        # Update and re-save
        run.pass_count = 8
        run.total_count = 10
        run.save()

        # Refresh from DB
        run.refresh_from_db()
        self.assertEqual(run.pass_rate, 80.0)

    def test_recalculates_when_total_goes_to_zero(self):
        """Setting total_count to 0 resets pass_rate to 0.00."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=6,
            total_count=10,
            pass_count=8,
        )
        self.assertEqual(run.pass_rate, 80.0)

        run.total_count = 0
        run.pass_count = 0
        run.save()
        run.refresh_from_db()
        self.assertEqual(run.pass_rate, 0)

    def test_rounding_two_decimals(self):
        """Pass rate is rounded to 2 decimal places."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=7,
            total_count=3,
            pass_count=1,
        )
        # 1/3 * 100 = 33.333... → 33.33
        self.assertEqual(run.pass_rate, 33.33)

    def test_single_test_pass(self):
        """Single passing test yields 100%."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=8,
            total_count=1,
            pass_count=1,
        )
        self.assertEqual(run.pass_rate, 100.0)

    def test_single_test_fail(self):
        """Single failing test yields 0%."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=9,
            total_count=1,
            pass_count=0,
            fail_count=1,
        )
        self.assertEqual(run.pass_rate, 0.0)

    def test_pass_rate_field_type(self):
        """pass_rate is stored as a Decimal-compatible value."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=10,
            total_count=7,
            pass_count=5,
        )
        # 5/7 * 100 = 71.4285... → 71.43
        self.assertEqual(run.pass_rate, 71.43)

    def test_pass_count_greater_than_total_still_computes(self):
        """Edge case: pass_count > total_count still computes (defensive)."""
        run = RegressionRun.objects.create(
            regression=self.regression,
            run_number=11,
            total_count=5,
            pass_count=10,
        )
        # 10/5 * 100 = 200.0
        self.assertEqual(run.pass_rate, 200.0)


class GetNextRunNumberTests(TestCase):
    """Tests for regressions/services.py :: get_next_run_number."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(name="Test Project")
        cls.regression = Regression.objects.create(
            project=cls.project,
            name="Test Regression",
        )
        cls.other_regression = Regression.objects.create(
            project=cls.project,
            name="Other Regression",
        )

    def test_no_runs_returns_one(self):
        """When no runs exist, the next number should be 1."""
        self.assertEqual(get_next_run_number(self.regression), 1)

    def test_single_run_returns_next(self):
        """When one run exists with run_number=1, next should be 2."""
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=1,
        )
        self.assertEqual(get_next_run_number(self.regression), 2)

    def test_increments_from_max_existing(self):
        """With multiple runs, next number is max(run_number) + 1."""
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=1,
        )
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=2,
        )
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=3,
        )
        self.assertEqual(get_next_run_number(self.regression), 4)

    def test_handles_non_contiguous_run_numbers(self):
        """When runs are not contiguous (e.g. 5, 10), next should be 11."""
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=5,
        )
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=10,
        )
        self.assertEqual(get_next_run_number(self.regression), 11)

    def test_regressions_are_independent(self):
        """Run numbers are scoped per regression — different regressions don't affect each other."""
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=1,
        )
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=2,
        )
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=3,
        )
        # Other regression has no runs — should still return 1
        self.assertEqual(get_next_run_number(self.other_regression), 1)

    def test_after_deleting_highest_run_number(self):
        """Deleting the highest run_number — next uses remaining max."""
        run3 = RegressionRun.objects.create(
            regression=self.regression,
            run_number=3,
        )
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=1,
        )
        run3.delete()
        # Max remaining is 1
        self.assertEqual(get_next_run_number(self.regression), 2)

    def test_returns_integer_not_none(self):
        """Return value is always an int, never None."""
        result = get_next_run_number(self.regression)
        self.assertIsInstance(result, int)
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=42,
        )
        result = get_next_run_number(self.regression)
        self.assertIsInstance(result, int)

    def test_zero_based_numbering_not_recycled(self):
        """If somehow run_number=0 exists, next should be 1 (max(0)=0 → 0+1=1)."""
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=0,
        )
        self.assertEqual(get_next_run_number(self.regression), 1)

    def test_large_run_numbers(self):
        """Works correctly with large run numbers."""
        RegressionRun.objects.create(
            regression=self.regression,
            run_number=999,
        )
        self.assertEqual(get_next_run_number(self.regression), 1000)


class RunListViewTests(TestCase):
    """Tests for RunListView — filtering by project, regression, status, trigger_type."""

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User
        from common.choices import RunStatus, TriggerType

        cls.user = User.objects.create_user(email="runviewer@example.com", username="runviewer", password="password")

        cls.project_a = Project.objects.create(name="Project A", owner=cls.user)
        cls.project_b = Project.objects.create(name="Project B", owner=cls.user)

        cls.reg_a1 = Regression.objects.create(project=cls.project_a, name="Reg A1", owner=cls.user, is_active=True)
        cls.reg_a2 = Regression.objects.create(project=cls.project_a, name="Reg A2", owner=cls.user, is_active=True)
        cls.reg_b1 = Regression.objects.create(project=cls.project_b, name="Reg B1", owner=cls.user, is_active=True)

        # Runs with different statuses and trigger types
        cls.run1 = RegressionRun.objects.create(
            regression=cls.reg_a1,
            run_number=1,
            status=RunStatus.COMPLETED,
            trigger_type=TriggerType.MANUAL,
        )
        cls.run2 = RegressionRun.objects.create(
            regression=cls.reg_a1,
            run_number=2,
            status=RunStatus.FAILED,
            trigger_type=TriggerType.CI,
        )
        cls.run3 = RegressionRun.objects.create(
            regression=cls.reg_a2,
            run_number=1,
            status=RunStatus.RUNNING,
            trigger_type=TriggerType.SCHEDULED,
        )
        cls.run4 = RegressionRun.objects.create(
            regression=cls.reg_b1,
            run_number=1,
            status=RunStatus.COMPLETED,
            trigger_type=TriggerType.MANUAL,
        )
        cls.run5 = RegressionRun.objects.create(
            regression=cls.reg_b1,
            run_number=2,
            status=RunStatus.PARTIAL,
            trigger_type=TriggerType.API,
        )

    def setUp(self):
        self.client.login(username="runviewer", password="password")

    def test_returns_all_runs_without_filters(self):
        """Unfiltered list returns all runs."""
        response = self.client.get(reverse("run-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "regressions/run_list.html")
        self.assertEqual(len(response.context["runs"]), 5)

    def test_filter_by_project(self):
        """project=<id> returns only runs from that project."""
        response = self.client.get(reverse("run-list"), {"project": self.project_a.pk})
        self.assertEqual(response.status_code, 200)
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 3)
        self.assertIn(self.run1.pk, run_ids)
        self.assertIn(self.run2.pk, run_ids)
        self.assertIn(self.run3.pk, run_ids)

    def test_filter_by_project_excludes_other(self):
        """project=<id> excludes runs from other projects."""
        response = self.client.get(reverse("run-list"), {"project": self.project_b.pk})
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 2)
        self.assertIn(self.run4.pk, run_ids)
        self.assertIn(self.run5.pk, run_ids)

    def test_filter_by_regession(self):
        """regression=<id> returns only runs from that regression."""
        response = self.client.get(reverse("run-list"), {"regression": self.reg_a1.pk})
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 2)
        self.assertIn(self.run1.pk, run_ids)
        self.assertIn(self.run2.pk, run_ids)

    def test_filter_by_status(self):
        """status=<status> returns only runs with that status."""
        from common.choices import RunStatus

        response = self.client.get(reverse("run-list"), {"status": RunStatus.COMPLETED})
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 2)
        self.assertIn(self.run1.pk, run_ids)
        self.assertIn(self.run4.pk, run_ids)

    def test_filter_by_trigger_type(self):
        """trigger_type=<type> returns only runs with that trigger type."""
        from common.choices import TriggerType

        response = self.client.get(reverse("run-list"), {"trigger_type": TriggerType.MANUAL})
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 2)
        self.assertIn(self.run1.pk, run_ids)
        self.assertIn(self.run4.pk, run_ids)

    def test_combined_project_and_status(self):
        """Applying both project and status filters returns intersection."""
        from common.choices import RunStatus

        response = self.client.get(reverse("run-list"), {"project": self.project_a.pk, "status": RunStatus.FAILED})
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 1)
        self.assertIn(self.run2.pk, run_ids)

    def test_combined_regession_and_trigger_type(self):
        """Applying both regression and trigger_type filters returns intersection."""
        from common.choices import TriggerType

        response = self.client.get(reverse("run-list"), {"regression": self.reg_b1.pk, "trigger_type": TriggerType.API})
        run_ids = {r.pk for r in response.context["runs"]}
        self.assertEqual(len(run_ids), 1)
        self.assertIn(self.run5.pk, run_ids)

    def test_nonexistent_project_returns_empty(self):
        """project=99999 returns no runs."""
        response = self.client.get(reverse("run-list"), {"project": 99999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["runs"]), 0)

    def test_nonexistent_status_returns_empty(self):
        """status=nonexistent returns no runs."""
        response = self.client.get(reverse("run-list"), {"status": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["runs"]), 0)

    def test_context_project_list(self):
        """Context includes project_list for filter dropdown."""
        response = self.client.get(reverse("run-list"))
        self.assertIn("project_list", response.context)

    def test_context_regression_list(self):
        """Context includes regression_list for filter dropdown."""
        response = self.client.get(reverse("run-list"))
        self.assertIn("regression_list", response.context)

    def test_paginate_by_is_20(self):
        """View paginates by 20 items per page."""
        response = self.client.get(reverse("run-list"))
        self.assertEqual(response.context["paginator"].per_page, 20)

    def test_uses_reverse_url(self):
        """Accessing via reverse URL name works."""
        response = self.client.get(reverse("run-list"))
        self.assertEqual(response.status_code, 200)


class RunCreateViewTests(TestCase):
    """Tests for RunCreateView — form rendering, submission, and auto run_number."""

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.staff_user = User.objects.create_user(
            email="staff@example.com", username="staff", password="password", is_staff=True
        )
        cls.non_staff_user = User.objects.create_user(
            email="nonstaff@example.com", username="nonstaff", password="password", is_staff=False
        )

        cls.project = Project.objects.create(name="Test Project", owner=cls.staff_user)
        cls.regression = Regression.objects.create(
            project=cls.project, name="Smoke Suite", owner=cls.staff_user, is_active=True
        )

    def test_staff_can_access_create_page(self):
        """Staff user can access the run creation form."""
        self.client.login(username="staff", password="password")
        response = self.client.get(reverse("run-create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "regressions/run_form.html")

    def test_non_staff_cannot_access_create_page(self):
        """Non-staff user is denied access (403 or redirect)."""
        self.client.login(username="nonstaff", password="password")
        response = self.client.get(reverse("run-create"))
        self.assertIn(response.status_code, [302, 403])

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated user is redirected to login."""
        response = self.client.get(reverse("run-create"))
        self.assertEqual(response.status_code, 302)

    def test_form_contains_regression_field(self):
        """Form includes the regression select field."""
        self.client.login(username="staff", password="password")
        response = self.client.get(reverse("run-create"))
        self.assertIn("regression", response.context["form"].fields)

    def test_create_run_auto_assigns_run_number(self):
        """Submitting without run_number auto-assigns the next number."""
        self.client.login(username="staff", password="password")
        response = self.client.post(
            reverse("run-create"),
            {
                "regression": self.regression.pk,
                "status": "queued",
                "trigger_type": "manual",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RegressionRun.objects.count(), 1)
        run = RegressionRun.objects.first()
        self.assertEqual(run.run_number, 1)

    def test_create_run_increments_run_number(self):
        """Second run gets run_number=2 when run_number=1 already exists."""
        RegressionRun.objects.create(regression=self.regression, run_number=1, status="completed")
        self.client.login(username="staff", password="password")
        response = self.client.post(
            reverse("run-create"),
            {
                "regression": self.regression.pk,
                "status": "queued",
                "trigger_type": "manual",
            },
        )
        self.assertEqual(response.status_code, 302)
        latest_run = RegressionRun.objects.filter(regression=self.regression).latest("pk")
        self.assertEqual(latest_run.run_number, 2)

    def test_create_run_form_does_not_include_run_number(self):
        """Form doesn't include run_number field — it's auto-assigned by the view."""
        self.client.login(username="staff", password="password")
        response = self.client.get(reverse("run-create"))
        self.assertNotIn("run_number", response.context["form"].fields)
        # Posting run_number is ignored; auto-assignment always applies
        response = self.client.post(
            reverse("run-create"),
            {
                "regression": self.regression.pk,
                "run_number": 42,  # ignored — field not in form
                "status": "queued",
                "trigger_type": "ci",
            },
        )
        self.assertEqual(response.status_code, 302)
        run = RegressionRun.objects.first()
        self.assertEqual(run.run_number, 1)

    def test_create_run_redirects_to_run_list(self):
        """Successful creation redirects to run list."""
        self.client.login(username="staff", password="password")
        response = self.client.post(
            reverse("run-create"),
            {
                "regression": self.regression.pk,
                "status": "queued",
                "trigger_type": "manual",
            },
        )
        self.assertRedirects(response, reverse("run-list"))

    def test_create_run_different_regression_independent_numbering(self):
        """Run numbers are independent per regression."""
        RegressionRun.objects.create(regression=self.regression, run_number=1)
        regression2 = Regression.objects.create(project=self.project, name="Full Suite", owner=self.staff_user)
        self.client.login(username="staff", password="password")
        response = self.client.post(
            reverse("run-create"),
            {
                "regression": regression2.pk,
                "status": "queued",
                "trigger_type": "manual",
            },
        )
        self.assertEqual(response.status_code, 302)
        run = RegressionRun.objects.filter(regression=regression2).first()
        self.assertEqual(run.run_number, 1)
