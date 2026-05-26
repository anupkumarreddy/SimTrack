"""Tests for results/services.py: signature hashing, creation, and counting."""

import hashlib

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from common.choices import FailureCategory, ResultStatus
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result
from results.services import (
    get_or_create_signature,
    normalize_and_hash_signature,
    update_signature_counts,
)


class NormalizeAndHashSignatureTests(TestCase):
    """Tests for results.services.normalize_and_hash_signature."""

    def test_returns_normalized_text_and_hash(self):
        """Returns (normalized, sha256_hexdigest) tuple."""
        normalized, sig_hash = normalize_and_hash_signature("DATA  Mismatch")
        self.assertEqual(normalized, "data mismatch")
        self.assertEqual(sig_hash, hashlib.sha256("data mismatch".encode("utf-8")).hexdigest())

    def test_same_input_produces_same_hash(self):
        """Case and whitespace differences produce identical hashes."""
        _, hash1 = normalize_and_hash_signature("Assertion error")
        _, hash2 = normalize_and_hash_signature("assertion   ERROR")
        self.assertEqual(hash1, hash2)

    def test_different_input_produces_different_hash(self):
        """Different error messages produce different hashes."""
        _, hash1 = normalize_and_hash_signature("timeout error")
        _, hash2 = normalize_and_hash_signature("data mismatch")
        self.assertNotEqual(hash1, hash2)

    def test_empty_string_returns_empty_and_valid_hash(self):
        """Empty string normalizes to empty and produces a valid SHA256."""
        normalized, sig_hash = normalize_and_hash_signature("")
        self.assertEqual(normalized, "")
        self.assertEqual(len(sig_hash), 64)
        self.assertEqual(sig_hash, hashlib.sha256("".encode()).hexdigest())

    def test_none_returns_empty_and_valid_hash(self):
        """None normalizes to empty string."""
        normalized, sig_hash = normalize_and_hash_signature(None)
        self.assertEqual(normalized, "")
        self.assertEqual(len(sig_hash), 64)

    def test_hash_is_consistent_across_calls(self):
        """Multiple calls with the same input return the same hash."""
        _, h1 = normalize_and_hash_signature("TIMEOUT after 60s")
        _, h2 = normalize_and_hash_signature("  timeout   AFTER 60S  ")
        _, h3 = normalize_and_hash_signature("Timeout After 60s")
        self.assertEqual(h1, h2)
        self.assertEqual(h2, h3)

    def test_special_characters_preserved_in_normalized_text(self):
        """Special characters like colons and parentheses are preserved."""
        normalized, _ = normalize_and_hash_signature("ERROR: assertion FAILED (line 42)")
        self.assertEqual(normalized, "error: assertion failed (line 42)")


class GetOrCreateSignatureTests(TestCase):
    """Tests for results.services.get_or_create_signature."""

    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", username="user", password="password")
        self.project = Project.objects.create(name="Test Project", owner=self.user)
        self.regression = Regression.objects.create(project=self.project, name="Test Regression", owner=self.user)
        self.run = RegressionRun.objects.create(regression=self.regression, run_number=1)

    def test_creates_new_signature(self):
        """A new signature is created with expected defaults."""
        sig, created = get_or_create_signature(self.run, "Data mismatch", category="design")
        self.assertTrue(created)
        self.assertEqual(sig.signature_title, "Data mismatch")
        self.assertEqual(sig.normalized_signature, "data mismatch")
        self.assertEqual(sig.signature_hash, hashlib.sha256("data mismatch".encode()).hexdigest())
        self.assertEqual(sig.category, "design")
        self.assertEqual(sig.result_count, 0)
        self.assertFalse(sig.is_known_issue)
        self.assertFalse(sig.is_infra_issue)
        self.assertEqual(sig.description, "")

    def test_returns_existing_signature(self):
        """Calling with the same (run, title) returns the existing signature."""
        sig1, created1 = get_or_create_signature(self.run, "Data mismatch", category="design")
        sig2, created2 = get_or_create_signature(self.run, "DATA  MISMATCH", category="config")
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(sig1.pk, sig2.pk)
        # Original values preserved
        self.assertEqual(sig2.signature_title, "Data mismatch")
        self.assertEqual(sig2.category, "design")

    def test_case_whitespace_normalization_for_duplicate_detection(self):
        """Signatures differing only in case/whitespace are treated as duplicates."""
        sig1, _ = get_or_create_signature(self.run, "  Assertion   Failed  ")
        sig2, created = get_or_create_signature(self.run, "ASSERTION failed")
        self.assertFalse(created)
        self.assertEqual(sig1.pk, sig2.pk)

    def test_category_defaults_to_unknown(self):
        """When no category is given, defaults to 'unknown'."""
        sig, _ = get_or_create_signature(self.run, "Some error")
        self.assertEqual(sig.category, FailureCategory.UNKNOWN)

    def test_sets_description(self):
        """Description is stored on new signature."""
        sig, _ = get_or_create_signature(self.run, "Timeout error", description="Test exceeded 60s limit")
        self.assertEqual(sig.description, "Test exceeded 60s limit")

    def test_sets_is_known_issue(self):
        """is_known_issue flag is set on new signature."""
        sig, _ = get_or_create_signature(self.run, "Known bug #123", is_known_issue=True)
        self.assertTrue(sig.is_known_issue)

    def test_sets_is_infra_issue(self):
        """is_infra_issue flag is set on new signature."""
        sig, _ = get_or_create_signature(self.run, "Disk full", is_infra_issue=True)
        self.assertTrue(sig.is_infra_issue)

    def test_different_run_same_title_creates_separate(self):
        """Same error title on different runs creates separate signatures."""
        run2 = RegressionRun.objects.create(regression=self.regression, run_number=2)
        sig1, _ = get_or_create_signature(self.run, "Data mismatch")
        sig2, created = get_or_create_signature(run2, "Data mismatch")
        self.assertTrue(created)
        self.assertNotEqual(sig1.pk, sig2.pk)

    def test_multiple_params_on_creation(self):
        """All optional params are set correctly on first creation."""
        sig, _ = get_or_create_signature(
            self.run,
            "Critical failure",
            category="design",
            description="Something broke badly",
            is_known_issue=True,
            is_infra_issue=False,
        )
        self.assertEqual(sig.signature_title, "Critical failure")
        self.assertEqual(sig.normalized_signature, "critical failure")
        self.assertEqual(sig.category, "design")
        self.assertEqual(sig.description, "Something broke badly")
        self.assertTrue(sig.is_known_issue)
        self.assertFalse(sig.is_infra_issue)


class UpdateSignatureCountsTests(TestCase):
    """Tests for results.services.update_signature_counts."""

    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", username="user", password="password")
        self.project = Project.objects.create(name="Test Project", owner=self.user)
        self.regression = Regression.objects.create(project=self.project, name="Test Regression", owner=self.user)
        self.run = RegressionRun.objects.create(regression=self.regression, run_number=1)
        self.signature = FailureSignature.objects.create(
            regression_run=self.run,
            signature_title="Data mismatch",
            signature_hash="abc123",
        )

    def _create_result(self, status=ResultStatus.FAIL):
        return Result.objects.create(
            regression_run=self.run,
            failure_signature=self.signature,
            test_name="test_read",
            status=status,
        )

    def test_zero_results_sets_count_to_zero(self):
        """Signature with no results has result_count = 0."""
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 0)

    def test_single_result_sets_count_to_one(self):
        """Signature with one result has result_count = 1."""
        self._create_result()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 1)

    def test_multiple_results_updates_count(self):
        """Signature with multiple results has correct count."""
        self._create_result()
        self._create_result()
        self._create_result()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 3)

    def test_count_updates_when_result_added(self):
        """Adding a new result after initial count update increments the count."""
        self._create_result()
        self._create_result()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 2)

        # Add another result
        self._create_result()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 3)

    def test_count_decreases_when_result_deleted(self):
        """Deleting a result after count update decrements the count."""
        r1 = self._create_result()
        r2 = self._create_result()
        r3 = self._create_result()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 3)

        # Delete one result
        r1.delete()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 2)

        # Delete all
        r2.delete()
        r3.delete()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 0)

    def test_count_only_counts_own_results(self):
        """Only results linked to this signature are counted."""
        other_sig = FailureSignature.objects.create(
            regression_run=self.run,
            signature_title="Timeout error",
            signature_hash="def456",
        )
        # Create results for both signatures
        self._create_result()
        self._create_result()
        Result.objects.create(
            regression_run=self.run,
            failure_signature=other_sig,
            test_name="test_timeout",
            status=ResultStatus.TIMEOUT,
        )

        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 2)

        update_signature_counts(other_sig)
        other_sig.refresh_from_db()
        self.assertEqual(other_sig.result_count, 1)

    def test_count_works_with_different_statuses(self):
        """Results with any status are counted (not just failures)."""
        for status in [ResultStatus.PASS, ResultStatus.FAIL, ResultStatus.TIMEOUT, ResultStatus.SKIPPED]:
            Result.objects.create(
                regression_run=self.run,
                failure_signature=self.signature,
                test_name=f"test_{status}",
                status=status,
            )
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 4)

    def test_count_is_independent_of_run(self):
        """Results across different runs linked to same signature are all counted."""
        run2 = RegressionRun.objects.create(regression=self.regression, run_number=2)
        Result.objects.create(
            regression_run=self.run,
            failure_signature=self.signature,
            test_name="test_run1",
            status=ResultStatus.FAIL,
        )
        Result.objects.create(
            regression_run=run2,
            failure_signature=self.signature,
            test_name="test_run2",
            status=ResultStatus.FAIL,
        )
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 2)

    def test_signature_with_null_result_from_different_sig_not_counted(self):
        """Results with failure_signature=NULL are not counted for any signature."""
        Result.objects.create(
            regression_run=self.run,
            failure_signature=None,
            test_name="orphan_result",
            status=ResultStatus.FAIL,
        )
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 0)

    def test_updates_only_specified_fields(self):
        """update_signature_counts only changes result_count and updated_at."""
        original_title = self.signature.signature_title
        self._create_result()
        update_signature_counts(self.signature)
        self.signature.refresh_from_db()
        # Title should be unchanged
        self.assertEqual(self.signature.signature_title, original_title)
        # Count should be updated
        self.assertEqual(self.signature.result_count, 1)


class ResultSignalTests(TestCase):
    """Tests for results/signals.py: post_save and post_delete signal effects."""

    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", username="user", password="password")
        self.project = Project.objects.create(name="Test Project", owner=self.user)
        self.regression = Regression.objects.create(project=self.project, name="Test Regression", owner=self.user)
        self.run = RegressionRun.objects.create(regression=self.regression, run_number=1)
        self.signature = FailureSignature.objects.create(
            regression_run=self.run,
            signature_title="Data mismatch",
            signature_hash="abc123",
        )

    def _create_result(self, status=ResultStatus.FAIL, failure_signature=None):
        return Result.objects.create(
            regression_run=self.run,
            failure_signature=failure_signature or self.signature,
            test_name="test_read",
            status=status,
        )

    # --- post_save: recalculate_run_counters ---

    def test_post_save_recalculates_run_counters(self):
        """Creating a Result updates the run's counter fields."""
        self._create_result()
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 1)
        self.assertEqual(self.run.fail_count, 1)
        self.assertEqual(self.run.pass_count, 0)

    def test_post_save_run_counters_multiple_results(self):
        """Creating multiple Results accumulates counters correctly."""
        for i in range(3):
            Result.objects.create(
                regression_run=self.run,
                test_name=f"test_{i}",
                status=ResultStatus.PASS,
            )
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 3)
        self.assertEqual(self.run.pass_count, 3)
        self.assertEqual(self.run.fail_count, 0)

    def test_post_save_run_counters_mixed_statuses(self):
        """Creating Results with mixed statuses updates all counter fields."""
        Result.objects.create(regression_run=self.run, test_name="t1", status=ResultStatus.PASS)
        Result.objects.create(regression_run=self.run, test_name="t2", status=ResultStatus.FAIL)
        Result.objects.create(regression_run=self.run, test_name="t3", status=ResultStatus.TIMEOUT)
        Result.objects.create(regression_run=self.run, test_name="t4", status=ResultStatus.KILLED)
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 4)
        self.assertEqual(self.run.pass_count, 1)
        self.assertEqual(self.run.fail_count, 1)
        self.assertEqual(self.run.timeout_count, 1)
        self.assertEqual(self.run.killed_count, 1)

    def test_post_save_run_counters_updates_pass_rate(self):
        """Creating Results recalculates the pass_rate on the run."""
        Result.objects.create(regression_run=self.run, test_name="t_pass", status=ResultStatus.PASS)
        Result.objects.create(regression_run=self.run, test_name="t_fail", status=ResultStatus.FAIL)
        self.run.refresh_from_db()
        self.assertEqual(self.run.pass_rate, 50.00)

    # --- post_save: update_signature_counts ---

    def test_post_save_updates_signature_counts(self):
        """Creating a Result linked to a signature updates its result_count."""
        self._create_result()
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 1)

    def test_post_save_signature_counts_multiple_results(self):
        """Creating multiple Results linked to the same signature accumulates the count."""
        self._create_result()
        self._create_result()
        self._create_result()
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 3)

    def test_post_save_signature_counts_only_own_results(self):
        """Only Results linked to this signature affect its count."""
        other_sig = FailureSignature.objects.create(
            regression_run=self.run,
            signature_title="Timeout error",
            signature_hash="def456",
        )
        self._create_result()
        self._create_result()
        Result.objects.create(
            regression_run=self.run,
            failure_signature=other_sig,
            test_name="test_other",
            status=ResultStatus.TIMEOUT,
        )
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 2)
        other_sig.refresh_from_db()
        self.assertEqual(other_sig.result_count, 1)

    # --- post_save: edge cases ---

    def test_post_save_null_failure_signature_no_error(self):
        """Creating a Result with null failure_signature doesn't crash."""
        result = Result.objects.create(
            regression_run=self.run,
            failure_signature=None,
            test_name="no_sig",
            status=ResultStatus.FAIL,
        )
        self.assertIsNotNone(result.pk)
        # Run counters should still update
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 1)

    def test_post_save_updating_result_recalculates_counters(self):
        """Updating an existing Result (e.g. changing status) triggers recalculate."""
        result = self._create_result()
        self.run.refresh_from_db()
        self.assertEqual(self.run.fail_count, 1)

        # Change status to pass
        result.status = ResultStatus.PASS
        result.save()
        self.run.refresh_from_db()
        self.assertEqual(self.run.pass_count, 1)
        self.assertEqual(self.run.fail_count, 0)

    def test_post_save_updating_result_different_run_no_crosstalk(self):
        """Updating a Result that moves between runs should work (though rare)."""
        run2 = RegressionRun.objects.create(regression=self.regression, run_number=2)
        result = self._create_result()
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 1)

        result.regression_run = run2
        result.save()
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 1)  # counted from query, not accumulate
        run2.refresh_from_db()
        self.assertEqual(run2.total_count, 1)

    # --- post_delete ---

    def test_post_delete_recalculates_run_counters(self):
        """Deleting a Result updates the run's counter fields."""
        result = self._create_result()
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 1)

        result.delete()
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 0)
        self.assertEqual(self.run.fail_count, 0)

    def test_post_delete_updates_signature_counts(self):
        """Deleting a Result linked to a signature decrements its result_count."""
        result = self._create_result()
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 1)

        result.delete()
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 0)

    def test_post_delete_removes_one_of_many(self):
        """Deleting one Result from many leaves correct remaining count."""
        r1 = self._create_result()
        self._create_result()
        self._create_result()
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 3)

        r1.delete()
        self.signature.refresh_from_db()
        self.assertEqual(self.signature.result_count, 2)

        self.run.refresh_from_db()
        self.assertEqual(self.run.total_count, 2)

    def test_post_delete_recalculates_pass_rate(self):
        """Deleting a Result recalculates the pass_rate."""
        Result.objects.create(regression_run=self.run, test_name="t1", status=ResultStatus.PASS)
        r2 = Result.objects.create(regression_run=self.run, test_name="t2", status=ResultStatus.FAIL)
        self.run.refresh_from_db()
        self.assertEqual(self.run.pass_rate, 50.00)

        r2.delete()
        self.run.refresh_from_db()
        self.assertEqual(self.run.pass_rate, 100.00)


class ResultListViewTests(TestCase):
    """Tests for results/views.py: ResultListView — filtering, pagination, context."""

    @classmethod
    def setUpTestData(cls):
        from accounts.models import User

        cls.user = User.objects.create_user(email="listviewer@example.com", username="listviewer", password="password")
        cls.project1 = Project.objects.create(name="Project Alpha")
        cls.project2 = Project.objects.create(name="Project Beta")

        cls.regression1 = Regression.objects.create(project=cls.project1, name="Smoke Suite", owner=cls.user)
        cls.regression2 = Regression.objects.create(project=cls.project2, name="Full Suite", owner=cls.user)

        cls.run1 = RegressionRun.objects.create(
            regression=cls.regression1, run_number=1, total_count=3, pass_count=2, fail_count=1, status="completed"
        )
        cls.run2 = RegressionRun.objects.create(
            regression=cls.regression2, run_number=1, total_count=2, pass_count=2, fail_count=0, status="completed"
        )

        cls.sig1 = FailureSignature.objects.create(
            regression_run=cls.run1, signature_title="Data mismatch", signature_hash="abc123"
        )

        cls.r_pass = Result.objects.create(regression_run=cls.run1, test_name="test_read", status=ResultStatus.PASS)
        cls.r_fail = Result.objects.create(
            regression_run=cls.run1, test_name="test_write_data", status=ResultStatus.FAIL, failure_signature=cls.sig1
        )
        cls.r_timeout = Result.objects.create(
            regression_run=cls.run1, test_name="test_timeout_check", status=ResultStatus.TIMEOUT
        )
        cls.r2_pass = Result.objects.create(
            regression_run=cls.run2, test_name="test_read_data", status=ResultStatus.PASS
        )
        cls.r2_fail = Result.objects.create(regression_run=cls.run2, test_name="test_assert", status=ResultStatus.FAIL)

    def setUp(self):
        self.client.login(username="listviewer", password="password")

    def test_returns_all_results_without_filters(self):
        """Unfiltered list returns all results."""
        response = self.client.get(reverse("result-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "results/result_list.html")
        self.assertEqual(len(response.context["results"]), 5)

    def test_filter_by_project(self):
        """project=ID returns only results for that project."""
        response = self.client.get(reverse("result-list"), {"project": self.project1.pk})
        results = list(response.context["results"])
        self.assertEqual(len(results), 3)
        self.assertIn(self.r_pass, results)
        self.assertIn(self.r_fail, results)
        self.assertIn(self.r_timeout, results)

    def test_filter_by_regression(self):
        """regression=ID returns only results for that regression."""
        response = self.client.get(reverse("result-list"), {"regression": self.regression2.pk})
        results = list(response.context["results"])
        self.assertEqual(len(results), 2)
        self.assertIn(self.r2_pass, results)
        self.assertIn(self.r2_fail, results)

    def test_filter_by_run(self):
        """run=ID returns only results for that run."""
        response = self.client.get(reverse("result-list"), {"run": self.run2.pk})
        self.assertEqual(len(response.context["results"]), 2)

    def test_filter_by_status(self):
        """status=fail returns only failed results."""
        response = self.client.get(reverse("result-list"), {"status": ResultStatus.FAIL})
        results = list(response.context["results"])
        self.assertEqual(len(results), 2)
        self.assertIn(self.r_fail, results)
        self.assertIn(self.r2_fail, results)

    def test_filter_by_status_pass(self):
        """status=pass returns only passing results."""
        response = self.client.get(reverse("result-list"), {"status": ResultStatus.PASS})
        self.assertEqual(len(response.context["results"]), 2)

    def test_filter_by_status_timeout(self):
        """status=timeout returns only timed-out results."""
        response = self.client.get(reverse("result-list"), {"status": ResultStatus.TIMEOUT})
        self.assertEqual(len(response.context["results"]), 1)
        self.assertEqual(response.context["results"][0], self.r_timeout)

    def test_filter_by_test_name(self):
        """test_name=read returns results matching test name."""
        response = self.client.get(reverse("result-list"), {"test_name": "read"})
        results = list(response.context["results"])
        self.assertEqual(len(results), 2)
        self.assertIn(self.r_pass, results)
        self.assertIn(self.r2_pass, results)

    def test_filter_by_test_name_case_insensitive(self):
        """test_name filter is case insensitive."""
        response = self.client.get(reverse("result-list"), {"test_name": "WRITE"})
        self.assertEqual(len(response.context["results"]), 1)
        self.assertEqual(response.context["results"][0], self.r_fail)

    def test_filter_by_signature(self):
        """signature=ID returns only results linked to that failure signature."""
        response = self.client.get(reverse("result-list"), {"signature": self.sig1.pk})
        self.assertEqual(len(response.context["results"]), 1)
        self.assertEqual(response.context["results"][0], self.r_fail)

    def test_filter_by_nonexistent_signature_returns_empty(self):
        """signature=99999 returns no results."""
        response = self.client.get(reverse("result-list"), {"signature": 99999})
        self.assertEqual(len(response.context["results"]), 0)

    def test_combined_project_and_status_filter(self):
        """Applying both project and status filters returns intersection."""
        response = self.client.get(reverse("result-list"), {"project": self.project1.pk, "status": ResultStatus.FAIL})
        self.assertEqual(len(response.context["results"]), 1)
        self.assertEqual(response.context["results"][0], self.r_fail)

    def test_combined_regression_and_test_name_filter(self):
        """Applying both regression and test_name filters returns intersection."""
        response = self.client.get(reverse("result-list"), {"regression": self.regression2.pk, "test_name": "assert"})
        self.assertEqual(len(response.context["results"]), 1)
        self.assertEqual(response.context["results"][0], self.r2_fail)

    def test_context_includes_filter_lists(self):
        """Context includes project_list, regression_list, run_list, signature_list."""
        response = self.client.get(reverse("result-list"))
        self.assertIn("project_list", response.context)
        self.assertIn("regression_list", response.context)
        self.assertIn("run_list", response.context)
        self.assertIn("signature_list", response.context)

    def test_context_object_name_is_results(self):
        """The context variable is named 'results'."""
        response = self.client.get(reverse("result-list"))
        self.assertIn("results", response.context)

    def test_paginate_by_is_50(self):
        """View paginates by 50 items per page."""
        response = self.client.get(reverse("result-list"))
        self.assertEqual(response.context["paginator"].per_page, 50)

    def test_queryset_select_related(self):
        """Queryset uses select_related for performance (no N+1 on access)."""
        response = self.client.get(reverse("result-list"))
        results = list(response.context["results"])
        # Accessing the FK without triggering additional queries
        for r in results:
            _ = r.regression_run.regression.project  # noqa: B018


class FailureSignatureDetailViewTests(TestCase):
    """Tests for results/views.py: FailureSignatureDetailView — rendering and context."""

    def setUp(self):
        self.user = User.objects.create_user(email="viewer@example.com", username="viewer", password="password")
        self.project = Project.objects.create(name="Test Project")
        self.regression = Regression.objects.create(project=self.project, name="Test Regression", owner=self.user)
        self.run = RegressionRun.objects.create(regression=self.regression, run_number=1)
        self.signature = FailureSignature.objects.create(
            regression_run=self.run,
            signature_title="Assertion Failed",
            normalized_signature="assertion failed",
            signature_hash="def456",
            category=FailureCategory.DESIGN,
            description="Known design bug",
            result_count=3,
            is_known_issue=True,
        )
        self.client.login(username="viewer", password="password")

    def test_detail_returns_200(self):
        """Signature detail page returns 200."""
        response = self.client.get(reverse("failure-signature-detail", kwargs={"pk": self.signature.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "results/failure_signature_detail.html")

    def test_context_object_is_signature(self):
        """Context 'signature' key contains the signature instance."""
        response = self.client.get(reverse("failure-signature-detail", kwargs={"pk": self.signature.pk}))
        self.assertEqual(response.context["signature"], self.signature)

    def test_context_includes_results(self):
        """Context includes 'results' linked to the signature."""
        Result.objects.create(
            regression_run=self.run, failure_signature=self.signature, test_name="t1", status=ResultStatus.FAIL
        )
        Result.objects.create(
            regression_run=self.run, failure_signature=self.signature, test_name="t2", status=ResultStatus.FAIL
        )
        response = self.client.get(reverse("failure-signature-detail", kwargs={"pk": self.signature.pk}))
        self.assertEqual(len(response.context["results"]), 2)

    def test_context_results_limited_to_50(self):
        """Results context is capped at 50 items."""
        for i in range(55):
            Result.objects.create(
                regression_run=self.run, failure_signature=self.signature, test_name=f"t_{i}", status=ResultStatus.FAIL
            )
        response = self.client.get(reverse("failure-signature-detail", kwargs={"pk": self.signature.pk}))
        self.assertEqual(len(response.context["results"]), 50)

    def test_nonexistent_signature_returns_404(self):
        """Requesting a non-existent signature returns 404."""
        response = self.client.get(reverse("failure-signature-detail", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)

    def test_signature_details_in_context(self):
        """All signature fields are accessible via context."""
        response = self.client.get(reverse("failure-signature-detail", kwargs={"pk": self.signature.pk}))
        sig = response.context["signature"]
        self.assertEqual(sig.category, FailureCategory.DESIGN)
        self.assertEqual(sig.description, "Known design bug")
        self.assertEqual(sig.result_count, 3)
        self.assertTrue(sig.is_known_issue)
