from datetime import timedelta

from django.test import TestCase
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
