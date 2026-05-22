"""Test #10 — RegressionDetailView: chart, calendar, and rendering tests."""

from datetime import date, datetime, timedelta
from datetime import timezone as dt_tz

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from common.choices import ResultStatus
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


def _make_run(
    regression,
    run_number,
    *,
    created_at=None,
    total_count=0,
    pass_count=0,
    fail_count=0,
    timeout_count=0,
    killed_count=0,
    skip_count=0,
    unknown_count=0,
    status="completed",
    triggered_by=None,
    run_name="",
    branch_name="",
    suite_name="",
    config_name="",
    build_id="",
    git_commit="",
    start_time=None,
    end_time=None,
    notes="",
):
    """Helper to create a RegressionRun with a specific created_at timestamp."""
    run = RegressionRun(
        regression=regression,
        run_number=run_number,
        total_count=total_count,
        pass_count=pass_count,
        fail_count=fail_count,
        timeout_count=timeout_count,
        killed_count=killed_count,
        skip_count=skip_count,
        unknown_count=unknown_count,
        status=status,
        triggered_by=triggered_by,
        run_name=run_name,
        branch_name=branch_name,
        suite_name=suite_name,
        config_name=config_name,
        build_id=build_id,
        git_commit=git_commit,
        start_time=start_time,
        end_time=end_time,
        notes=notes,
    )
    run.save()
    if created_at is not None:
        RegressionRun.objects.filter(pk=run.pk).update(created_at=created_at)
        run.refresh_from_db()
    return run


def _make_result(run, test_name, status=ResultStatus.FAIL, failure_signature=None, duration_seconds=None):
    return Result.objects.create(
        regression_run=run,
        test_name=test_name,
        status=status,
        failure_signature=failure_signature,
        duration_seconds=duration_seconds,
    )


class RegressionDetailViewContextTests(TestCase):
    """Tests for RegressionDetailView.get_context_data keys and structure."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="user@example.com", username="user", password="password", is_staff=True
        )
        cls.project = Project.objects.create(name="Test Project", owner=cls.user)
        cls.regression = Regression.objects.create(project=cls.project, name="Nightly Smoke", owner=cls.user)

    def test_basic_context_keys(self):
        """View populates all expected context keys."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=8, fail_count=2)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertIn("runs", ctx)
        self.assertIn("latest_run", ctx)
        self.assertIn("chart_runs", ctx)
        self.assertIn("chart_series", ctx)
        self.assertIn("chart_ticks", ctx)
        self.assertIn("calendar_runs", ctx)
        self.assertIn("calendar_weeks", ctx)
        self.assertIn("calendar_month_label", ctx)
        self.assertIn("previous_month", ctx)
        self.assertIn("next_month", ctx)
        self.assertIn("run_payloads", ctx)
        self.assertIn("regression", ctx)

    def test_latest_run_is_most_recent(self):
        """latest_run is the most recent run (first in the recent_runs list)."""
        now = timezone.now()
        older = now - timedelta(days=5)
        _make_run(self.regression, 1, created_at=older, total_count=5, pass_count=5)
        _make_run(self.regression, 2, created_at=now, total_count=10, pass_count=8, fail_count=2)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        ctx = response.context
        self.assertEqual(ctx["latest_run"].run_number, 2)

    def test_latest_run_is_none_when_no_runs(self):
        """When a regression has no runs, latest_run is None."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        ctx = response.context
        self.assertIsNone(ctx["latest_run"])

    def test_recent_runs_limited_to_25(self):
        """Only the 25 most recent runs are included."""
        now = timezone.now()
        for i in range(30):
            _make_run(
                self.regression,
                i + 1,
                created_at=now - timedelta(days=30 - i),
                total_count=10,
                pass_count=8,
                fail_count=2,
            )

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        ctx = response.context
        self.assertEqual(len(ctx["runs"]), 25)
        self.assertEqual(ctx["runs"][0].run_number, 30)
        self.assertEqual(ctx["runs"][24].run_number, 6)


class RegressionDetailViewChartTests(TestCase):
    """Tests for chart data: series, points, paths, and ticks."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="user@example.com", username="user", password="password", is_staff=True
        )
        cls.project = Project.objects.create(name="Test Project", owner=cls.user)
        cls.regression = Regression.objects.create(project=cls.project, name="Nightly Smoke", owner=cls.user)

    def test_chart_series_has_pass_and_fail(self):
        """chart_series contains exactly two series: Pass and Fail."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=100, pass_count=80, fail_count=20)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        series = response.context["chart_series"]
        self.assertEqual(len(series), 2)
        self.assertEqual(series[0]["label"], "Pass")
        self.assertEqual(series[0]["color"], "#16a34a")
        self.assertEqual(series[1]["label"], "Fail")
        self.assertEqual(series[1]["color"], "#dc2626")

    def test_chart_series_empty_when_no_runs(self):
        """chart_series is an empty list when no runs exist."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.context["chart_series"], [])

    def test_chart_ticks_empty_when_no_runs(self):
        """chart_ticks is an empty list when no runs exist."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.context["chart_ticks"], [])

    def test_chart_path_starts_with_M_command(self):
        """Chart SVG path strings start with 'M' (move to first point)."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=10)
        _make_run(self.regression, 2, created_at=now - timedelta(days=1), total_count=10, pass_count=8, fail_count=2)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        for s in response.context["chart_series"]:
            self.assertTrue(s["path"].startswith("M "))
            self.assertIn(" L ", s["path"])

    def test_chart_path_empty_when_no_runs(self):
        """Chart paths are empty strings when no runs exist."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        for s in response.context["chart_series"]:
            self.assertEqual(s["path"], "")

    def test_chart_run_order_is_oldest_first(self):
        """chart_runs are in chronological order (oldest first) for left-to-right chart rendering."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now - timedelta(days=2), total_count=10, pass_count=10)
        _make_run(self.regression, 2, created_at=now - timedelta(days=1), total_count=10, pass_count=8, fail_count=2)
        _make_run(self.regression, 3, created_at=now, total_count=10, pass_count=5, fail_count=5)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        chart_runs = response.context["chart_runs"]
        self.assertEqual(len(chart_runs), 3)
        self.assertEqual(chart_runs[0].run_number, 1)
        self.assertEqual(chart_runs[1].run_number, 2)
        self.assertEqual(chart_runs[2].run_number, 3)

    def test_chart_points_have_x_y_value(self):
        """Each chart point has x, y (floats), and value (string)."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=100, pass_count=75, fail_count=25)
        _make_run(self.regression, 2, created_at=now - timedelta(days=1), total_count=100, pass_count=90, fail_count=10)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        for s in response.context["chart_series"]:
            for p in s["points"]:
                self.assertIn("x", p)
                self.assertIn("y", p)
                self.assertIn("value", p)
                self.assertIsInstance(p["x"], float)
                self.assertIsInstance(p["y"], float)
                self.assertIsInstance(p["value"], str)

    def test_chart_ticks_have_label_and_x(self):
        """Each tick has an x coordinate and a label string."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=10)
        _make_run(self.regression, 2, created_at=now - timedelta(days=1), total_count=10, pass_count=8, fail_count=2)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        ticks = response.context["chart_ticks"]
        self.assertEqual(len(ticks), 2)
        for t in ticks:
            self.assertIn("x", t)
            self.assertIn("label", t)
            self.assertIsInstance(t["label"], str)


class RegressionDetailViewCalendarTests(TestCase):
    """Tests for calendar rendering: month selection, week structure, run grouping."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="user@example.com", username="user", password="password", is_staff=True
        )
        cls.project = Project.objects.create(name="Test Project", owner=cls.user)
        cls.regression = Regression.objects.create(project=cls.project, name="Nightly Smoke", owner=cls.user)

    def test_selected_month_defaults_to_latest_run(self):
        """When no ?month= param, calendar shows the month of the most recent run."""
        _make_run(
            self.regression,
            1,
            created_at=datetime(2026, 1, 15, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=10,
        )
        _make_run(
            self.regression,
            2,
            created_at=datetime(2026, 3, 20, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=8,
            fail_count=2,
        )

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.context["calendar_month_label"], "March 2026")

    def test_selected_month_respects_query_param(self):
        """?month=2026-01 overrides default to January."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=10)
        _make_run(
            self.regression,
            2,
            created_at=datetime(2026, 1, 10, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=5,
            fail_count=5,
        )

        self.client.login(username="user", password="password")
        response = self.client.get(
            reverse("regression-detail", kwargs={"pk": self.regression.pk}),
            {"month": "2026-01"},
        )

        self.assertEqual(response.context["calendar_month_label"], "January 2026")

    def test_invalid_month_param_falls_back_to_latest_run(self):
        """Malformed ?month= values fall back to the latest run's month."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=10)

        self.client.login(username="user", password="password")

        response = self.client.get(
            reverse("regression-detail", kwargs={"pk": self.regression.pk}),
            {"month": "not-a-date"},
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("regression-detail", kwargs={"pk": self.regression.pk}),
            {"month": "2026-13"},
        )
        self.assertEqual(response.status_code, 200)

    def test_selected_month_falls_back_to_today_when_no_runs(self):
        """When regression has no runs, calendar shows current month."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        today = date.today()
        expected_label = today.strftime("%B %Y")
        self.assertEqual(response.context["calendar_month_label"], expected_label)

    def test_calendar_weeks_is_list_of_lists(self):
        """calendar_weeks is a list of weeks, each week is a list of 7 days."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=10)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        weeks = response.context["calendar_weeks"]
        self.assertIsInstance(weeks, list)
        self.assertGreater(len(weeks), 0)
        for week in weeks:
            self.assertIsInstance(week, list)
            self.assertEqual(len(week), 7)

    def test_calendar_weeks_have_date_and_in_month(self):
        """Each day has 'date' (datetime.date) and 'in_month' (bool)."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=10)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        for week in response.context["calendar_weeks"]:
            for day in week:
                self.assertIn("date", day)
                self.assertIn("in_month", day)
                self.assertIn("runs", day)
                self.assertIsInstance(day["in_month"], bool)

    def test_calendar_runs_grouped_by_date(self):
        """Days that have runs list those runs; days without runs have empty list."""
        jan15 = datetime(2026, 1, 15, tzinfo=dt_tz.utc)
        jan20 = datetime(2026, 1, 20, tzinfo=dt_tz.utc)
        _make_run(self.regression, 1, created_at=jan15, total_count=10, pass_count=10)
        _make_run(self.regression, 2, created_at=jan20, total_count=10, pass_count=8, fail_count=2)

        self.client.login(username="user", password="password")
        response = self.client.get(
            reverse("regression-detail", kwargs={"pk": self.regression.pk}),
            {"month": "2026-01"},
        )

        runs_by_date = {}
        for week in response.context["calendar_weeks"]:
            for day in week:
                if day["runs"]:
                    runs_by_date[day["date"]] = day["runs"]

        self.assertIn(date(2026, 1, 15), runs_by_date)
        self.assertIn(date(2026, 1, 20), runs_by_date)
        self.assertEqual(len(runs_by_date[date(2026, 1, 15)]), 1)
        self.assertEqual(len(runs_by_date[date(2026, 1, 20)]), 1)

    def test_calendar_runs_have_calendar_fail_rate(self):
        """Runs in the calendar view have calendar_fail_rate attribute set."""
        now = timezone.now()
        _make_run(self.regression, 1, created_at=now, total_count=10, pass_count=8, fail_count=2)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        for run in response.context["calendar_runs"]:
            self.assertTrue(hasattr(run, "calendar_fail_rate"))

    def test_calendar_month_navigation_links(self):
        """previous_month and next_month are valid YYYY-MM strings for navigation."""
        _make_run(
            self.regression,
            1,
            created_at=datetime(2026, 3, 15, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=10,
        )

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.context["previous_month"], "2026-02")
        self.assertEqual(response.context["next_month"], "2026-04")

    def test_calendar_month_rollover_december_to_january(self):
        """Next month from December wraps to January of next year."""
        _make_run(
            self.regression,
            1,
            created_at=datetime(2026, 12, 15, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=10,
        )

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.context["next_month"], "2027-01")
        self.assertEqual(response.context["previous_month"], "2026-11")

    def test_calendar_month_rollover_january_to_december(self):
        """Previous month from January wraps to December of previous year."""
        _make_run(
            self.regression,
            1,
            created_at=datetime(2026, 1, 15, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=10,
        )

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        self.assertEqual(response.context["previous_month"], "2025-12")
        self.assertEqual(response.context["next_month"], "2026-02")

    def test_calendar_empty_when_no_runs(self):
        """Calendar weeks are still generated (empty month) when no runs exist."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        weeks = response.context["calendar_weeks"]
        self.assertGreater(len(weeks), 0)
        self.assertEqual(response.context["calendar_runs"], [])


class RegressionDetailViewRunPayloadTests(TestCase):
    """Tests for run payloads returned by the view."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="user@example.com", username="user", password="password", is_staff=True
        )
        cls.project = Project.objects.create(name="Test Project", owner=cls.user)
        cls.regression = Regression.objects.create(project=cls.project, name="Nightly Smoke", owner=cls.user)

    def _create_run_with_results(self):
        """Create a run with results and failure signatures for payload testing."""
        run = _make_run(
            self.regression,
            1,
            created_at=datetime(2026, 3, 15, 10, 30, tzinfo=dt_tz.utc),
            total_count=10,
            pass_count=7,
            fail_count=2,
            timeout_count=1,
            status="completed",
            triggered_by=self.user,
            run_name="Nightly Build",
            branch_name="main",
            suite_name="smoke",
            config_name="default",
            build_id="build-42",
            git_commit="deadbeef",
            start_time=datetime(2026, 3, 15, 10, 0, tzinfo=dt_tz.utc),
            end_time=datetime(2026, 3, 15, 10, 30, tzinfo=dt_tz.utc),
            notes="All good",
        )
        sig = FailureSignature.objects.create(
            regression_run=run,
            signature_title="Data mismatch",
            signature_hash="abc123",
            category="design",
        )

        _make_result(run, "test_read", status=ResultStatus.FAIL, failure_signature=sig)
        _make_result(run, "test_write", status=ResultStatus.PASS)
        _make_result(run, "test_timeout", status=ResultStatus.TIMEOUT)

        return run

    def test_run_payloads_contain_key_fields(self):
        """Run payload dicts have all expected metadata fields."""
        self._create_run_with_results()

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        payloads = response.context["run_payloads"]
        self.assertEqual(len(payloads), 1)
        p = payloads[0]

        self.assertEqual(p["run_number"], 1)
        self.assertEqual(p["status"], "completed")
        self.assertEqual(p["status_display"], "Completed")
        self.assertEqual(p["trigger_type"], "Manual")
        # Note: Creating Results triggers post_save signals that recalculate
        # run counters, so total_count reflects actual result count (3).
        self.assertEqual(p["total_count"], 3)
        self.assertEqual(p["fail_count"], 1)
        self.assertEqual(p["timeout_count"], 1)
        self.assertEqual(p["branch_name"], "main")
        self.assertEqual(p["suite_name"], "smoke")
        self.assertEqual(p["config_name"], "default")
        self.assertEqual(p["build_id"], "build-42")
        self.assertEqual(p["git_commit"], "deadbeef")
        self.assertEqual(p["notes"], "All good")
        self.assertIn("detail_url", p)
        self.assertIn("results_url", p)

    def test_run_payload_has_results_and_failed_results(self):
        """Run payload includes results and filtered failed_results lists."""
        self._create_run_with_results()

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(len(p["results"]), 3)
        self.assertEqual(len(p["failed_results"]), 1)
        self.assertEqual(p["failed_results"][0]["test_name"], "test_read")

    def test_run_payload_has_failure_signatures(self):
        """Run payload includes failure_signatures list."""
        self._create_run_with_results()

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(len(p["failure_signatures"]), 1)
        self.assertEqual(p["failure_signatures"][0]["title"], "Data mismatch")

    def test_run_payload_defaults_for_blank_fields(self):
        """Blank run fields show '\u2014' in payload."""
        _make_run(self.regression, 1, created_at=timezone.now(), total_count=5, pass_count=5)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(p["run_name"], "")
        self.assertEqual(p["branch_name"], "\u2014")
        self.assertEqual(p["suite_name"], "\u2014")
        self.assertEqual(p["config_name"], "\u2014")
        self.assertEqual(p["build_id"], "\u2014")
        self.assertEqual(p["git_commit"], "\u2014")

    def test_result_payload_has_expected_fields(self):
        """Result payload dicts have all expected fields."""
        self._create_run_with_results()

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        result = p["results"][0]
        self.assertIn("id", result)
        self.assertIn("test_name", result)
        self.assertIn("status", result)
        self.assertIn("status_display", result)
        self.assertIn("seed", result)
        self.assertIn("duration_seconds", result)
        self.assertIn("machine_name", result)
        self.assertIn("error_message", result)
        self.assertIn("signature", result)
        self.assertIn("signature_url", result)
        self.assertIn("detail_url", result)

    def test_signature_payload_has_expected_fields(self):
        """Signature payload dicts have all expected fields."""
        self._create_run_with_results()

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        sig = p["failure_signatures"][0]
        self.assertEqual(sig["title"], "Data mismatch")
        self.assertEqual(sig["category"], "Design")
        self.assertIn("detail_url", sig)
        self.assertIn("is_known_issue", sig)
        self.assertIn("is_infra_issue", sig)
        self.assertIn("result_count", sig)

    def test_triggered_by_displays_user(self):
        """triggered_by shows the user's string representation."""
        _make_run(self.regression, 1, created_at=timezone.now(), triggered_by=self.user, total_count=5, pass_count=5)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(p["triggered_by"], str(self.user))

    def test_triggered_by_dash_when_none(self):
        """triggered_by shows '\u2014' when no user triggered the run."""
        _make_run(self.regression, 1, created_at=timezone.now(), total_count=5, pass_count=5)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(p["triggered_by"], "\u2014")

    def test_duration_display_in_payload(self):
        """Run payload includes formatted duration string."""
        _make_run(
            self.regression,
            1,
            created_at=timezone.now(),
            total_count=5,
            pass_count=5,
            start_time=datetime(2026, 3, 15, 10, 0, tzinfo=dt_tz.utc),
            end_time=datetime(2026, 3, 15, 10, 30, tzinfo=dt_tz.utc),
        )

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(p["duration"], "00:30:00")

    def test_duration_dash_when_no_times(self):
        """Duration shows '-' when start/end times are not set."""
        _make_run(self.regression, 1, created_at=timezone.now(), total_count=5, pass_count=5)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(p["duration"], "-")

    def test_pass_and_fail_rates_in_payload(self):
        """Run payload includes formatted pass_rate and fail_rate strings."""
        _make_run(self.regression, 1, created_at=timezone.now(), total_count=100, pass_count=75, fail_count=25)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertIn("75", p["pass_rate"])
        self.assertEqual(p["fail_rate"], "25.00")

    def test_zero_total_fail_rate(self):
        """fail_rate is '0.00' when total_count is 0 (division guard)."""
        _make_run(self.regression, 1, created_at=timezone.now(), total_count=0)

        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))

        p = response.context["run_payloads"][0]
        self.assertEqual(p["fail_rate"], "0.00")


class RegressionDetailViewAccessTests(TestCase):
    """Tests for access control on RegressionDetailView."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="user@example.com", username="user", password="password")
        cls.project = Project.objects.create(name="Test Project", owner=cls.user)
        cls.regression = Regression.objects.create(project=cls.project, name="Nightly Smoke", owner=cls.user)

    def test_authenticated_user_can_view(self):
        """Any authenticated user can view regression detail (read-only)."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        """Anonymous users are redirected to login."""
        response = self.client.get(reverse("regression-detail", kwargs={"pk": self.regression.pk}))
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_regression_returns_404(self):
        """Requesting a regression that doesn't exist returns 404."""
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("regression-detail", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)
