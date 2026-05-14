from django.test import TestCase

from projects.models import Project
from regressions.models import Regression, RegressionRun
from regressions.services import get_next_run_number


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
