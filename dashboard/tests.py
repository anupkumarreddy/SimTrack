"""Tests for dashboard/views.py: DashboardView and ProjectDashboardView context data."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from common.choices import FailureCategory, MilestoneStatus, ResultStatus, RunStatus
from milestones.models import Milestone
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


class DashboardViewTests(TestCase):
    """Tests for DashboardView — global dashboard aggregation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="dashviewer@example.com", username="dashviewer", password="password")

        # --- Projects ---
        cls.project_a = Project.objects.create(name="AXI VIP", owner=cls.user)
        cls.project_b = Project.objects.create(name="PCIe Controller", owner=cls.user)
        cls.project_c = Project.objects.create(name="Empty Project")  # no regressions/runs

        # --- Regressions for project_a ---
        cls.reg_a1 = Regression.objects.create(
            project=cls.project_a, name="Smoke Suite", owner=cls.user, is_active=True
        )
        cls.reg_a2 = Regression.objects.create(project=cls.project_a, name="Full Suite", owner=cls.user, is_active=True)

        # --- Regressions for project_b (worse pass rate) ---
        cls.reg_b1 = Regression.objects.create(
            project=cls.project_b, name="B1 Regression", owner=cls.user, is_active=True
        )

        # --- Runs for project_a regressions ---
        RegressionRun.objects.create(
            regression=cls.reg_a1,
            run_number=1,
            total_count=100,
            pass_count=90,
            fail_count=10,
            status=RunStatus.COMPLETED,
        )
        RegressionRun.objects.create(
            regression=cls.reg_a2,
            run_number=1,
            total_count=200,
            pass_count=180,
            fail_count=20,
            status=RunStatus.COMPLETED,
        )

        # --- Runs for project_b regression (high fail rate) ---
        RegressionRun.objects.create(
            regression=cls.reg_b1,
            run_number=1,
            total_count=50,
            pass_count=10,
            fail_count=40,
            status=RunStatus.COMPLETED,
        )

        # --- Milestones ---
        cls.m1 = Milestone.objects.create(
            project=cls.project_a,
            title="AXI Milestone 1",
            status=MilestoneStatus.COMPLETED,
            owner=cls.user,
            target_date=timezone.now().date() - timedelta(days=10),
        )
        cls.m2 = Milestone.objects.create(
            project=cls.project_a,
            title="AXI Milestone 2",
            status=MilestoneStatus.IN_PROGRESS,
            owner=cls.user,
            target_date=timezone.now().date() + timedelta(days=30),
        )
        cls.m3 = Milestone.objects.create(
            project=cls.project_b,
            title="PCIe Milestone",
            status=MilestoneStatus.PLANNED,
            owner=cls.user,
            target_date=timezone.now().date() + timedelta(days=7),
        )

        # --- FailureSignatures ---
        run_a = cls.reg_a1.runs.first()
        run_b = cls.reg_b1.runs.first()
        cls.sig1 = FailureSignature.objects.create(
            regression_run=run_a,
            signature_title="Data mismatch",
            normalized_signature="data mismatch",
            signature_hash="aaa",
            category=FailureCategory.DESIGN,
            result_count=15,
        )
        cls.sig2 = FailureSignature.objects.create(
            regression_run=run_b,
            signature_title="Timeout error",
            normalized_signature="timeout error",
            signature_hash="bbb",
            category=FailureCategory.TIMEOUT,
            result_count=30,
        )

    def setUp(self):
        self.client.login(username="dashviewer", password="password")

    # --- Total counts ---

    def test_total_projects_count(self):
        """total_projects reflects all projects."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_projects"], 3)

    def test_total_regressions_count(self):
        """total_regressions counts all regressions."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_regressions"], 3)

    def test_total_runs_count(self):
        """total_runs counts all regression runs."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_runs"], 3)

    def test_total_milestones_count(self):
        """total_milestones counts all milestones."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_milestones"], 3)

    # --- Project rows ---

    def test_project_rows_count(self):
        """One row per project."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(len(response.context["project_rows"]), 3)

    def test_project_row_pass_rate(self):
        """Pass rate correctly calculated per project."""
        response = self.client.get(reverse("dashboard"))
        axi_row = next(r for r in response.context["project_rows"] if r["project"] == self.project_a)
        # (90 + 180) / (100 + 200) = 270/300 = 90.00%
        self.assertEqual(axi_row["pass_rate"], "90.00")
        self.assertAlmostEqual(axi_row["pass_rate_value"], 90.0, places=1)

    def test_project_row_pass_rate_zero_tests(self):
        """Project with no runs has 0 pass rate, no division error."""
        response = self.client.get(reverse("dashboard"))
        empty_row = next(r for r in response.context["project_rows"] if r["project"] == self.project_c)
        self.assertEqual(empty_row["pass_rate"], "0.00")
        self.assertEqual(empty_row["pass_rate_value"], 0)

    def test_project_row_run_and_regression_counts(self):
        """Project row includes correct run and regression counts."""
        response = self.client.get(reverse("dashboard"))
        axi_row = next(r for r in response.context["project_rows"] if r["project"] == self.project_a)
        self.assertEqual(axi_row["run_count"], 2)
        self.assertEqual(axi_row["regression_count"], 2)

    def test_project_row_milestone_counts(self):
        """Project row includes milestone and completed milestone counts."""
        response = self.client.get(reverse("dashboard"))
        axi_row = next(r for r in response.context["project_rows"] if r["project"] == self.project_a)
        self.assertEqual(axi_row["milestone_count"], 2)
        self.assertEqual(axi_row["completed_milestone_count"], 1)
        self.assertEqual(axi_row["milestone_rate"], "50")

    def test_project_row_milestone_rate_zero(self):
        """Project with no milestones has 0 milestone_rate, no division error."""
        response = self.client.get(reverse("dashboard"))
        empty_row = next(r for r in response.context["project_rows"] if r["project"] == self.project_c)
        self.assertEqual(empty_row["milestone_rate"], "0")

    def test_project_rows_ordered_by_name(self):
        """Project rows are sorted alphabetically by project name."""
        response = self.client.get(reverse("dashboard"))
        names = [r["project"].name for r in response.context["project_rows"]]
        self.assertEqual(names, sorted(names))

    # --- Regression rows ---

    def test_top_failing_regressions_count(self):
        """top_failing_regressions returns at most 5 items."""
        response = self.client.get(reverse("dashboard"))
        self.assertLessEqual(len(response.context["top_failing_regressions"]), 5)

    def test_top_failing_regressions_order(self):
        """Regressions sorted by highest fail rate first."""
        response = self.client.get(reverse("dashboard"))
        failing = response.context["top_failing_regressions"]
        rates = [r["fail_rate_value"] for r in failing]
        self.assertEqual(rates, sorted(rates, reverse=True))

    def test_top_failing_regressions_highest(self):
        """reg_b1 (80% fail rate) is the top failing."""
        response = self.client.get(reverse("dashboard"))
        top = response.context["top_failing_regressions"][0]
        self.assertEqual(top["regression"], self.reg_b1)
        self.assertAlmostEqual(top["fail_rate_value"], 80.0, places=1)

    def test_top_passing_regressions_order(self):
        """Regressions sorted by highest pass rate first."""
        response = self.client.get(reverse("dashboard"))
        passing = response.context["top_passing_regressions"]
        rates = [r["pass_rate_value"] for r in passing]
        self.assertEqual(rates, sorted(rates, reverse=True))

    def test_top_passing_regressions_highest(self):
        """reg_a1 and reg_a2 (both 90% pass rate) are at the top."""
        response = self.client.get(reverse("dashboard"))
        top = response.context["top_passing_regressions"][0]
        self.assertIn(top["regression"], [self.reg_a1, self.reg_a2])
        self.assertAlmostEqual(top["pass_rate_value"], 90.0, places=1)

    # --- Upcoming milestones ---

    def test_upcoming_milestones_future_only(self):
        """Only milestones with target_date >= today are included."""
        response = self.client.get(reverse("dashboard"))
        upcoming = response.context["upcoming_milestones"]
        for m in upcoming:
            self.assertGreaterEqual(m.target_date, timezone.now().date())

    def test_upcoming_milestones_order(self):
        """Ordered by target_date ascending, then project name."""
        response = self.client.get(reverse("dashboard"))
        upcoming = response.context["upcoming_milestones"]
        dates = [m.target_date for m in upcoming]
        self.assertEqual(dates, sorted(dates))

    def test_upcoming_milestones_limit(self):
        """At most 5 upcoming milestones."""
        response = self.client.get(reverse("dashboard"))
        self.assertLessEqual(len(response.context["upcoming_milestones"]), 5)

    # --- Top failure signatures ---

    def test_top_signatures_count(self):
        """At most 5 top failure signatures."""
        response = self.client.get(reverse("dashboard"))
        self.assertLessEqual(len(response.context["top_signatures"]), 5)

    def test_top_signatures_ordered_by_result_count(self):
        """Ordered by result_count descending."""
        response = self.client.get(reverse("dashboard"))
        sigs = response.context["top_signatures"]
        counts = [s.result_count for s in sigs]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_top_signatures_highest_first(self):
        """sig2 (result_count=30) appears before sig1 (result_count=15)."""
        response = self.client.get(reverse("dashboard"))
        top = response.context["top_signatures"]
        self.assertEqual(top[0], self.sig2)

    # --- Empty dashboard ---

    def test_empty_dashboard_no_errors(self):
        """Dashboard renders with no projects, regressions, runs, or milestones."""
        # Delete all data
        Result.objects.all().delete()
        FailureSignature.objects.all().delete()
        RegressionRun.objects.all().delete()
        Regression.objects.all().delete()
        Milestone.objects.all().delete()
        Project.objects.all().delete()

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_projects"], 0)
        self.assertEqual(response.context["total_regressions"], 0)
        self.assertEqual(response.context["total_runs"], 0)
        self.assertEqual(response.context["total_milestones"], 0)
        self.assertEqual(len(response.context["project_rows"]), 0)
        self.assertEqual(len(response.context["top_failing_regressions"]), 0)
        self.assertEqual(len(response.context["top_passing_regressions"]), 0)
        self.assertEqual(len(response.context["upcoming_milestones"]), 0)
        self.assertEqual(len(response.context["top_signatures"]), 0)

    def test_uses_reverse_url(self):
        """Accessing via reverse URL name works."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")

    def test_alt_url_works(self):
        """Accessing via dashboard-alt URL works."""
        response = self.client.get(reverse("dashboard-alt"))
        self.assertEqual(response.status_code, 200)


class ProjectDashboardViewTests(TestCase):
    """Tests for ProjectDashboardView — per-project dashboard context."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="projdash@example.com", username="projdash", password="password")
        cls.project = Project.objects.create(name="Test Project", owner=cls.user, slug="test-project")
        cls.other_project = Project.objects.create(name="Other Project", owner=cls.user, slug="other-project")

        # --- Regressions (some inactive) ---
        cls.reg1 = Regression.objects.create(project=cls.project, name="Active Reg 1", owner=cls.user, is_active=True)
        cls.reg2 = Regression.objects.create(project=cls.project, name="Active Reg 2", owner=cls.user, is_active=True)
        Regression.objects.create(project=cls.project, name="Inactive Reg", owner=cls.user, is_active=False)
        Regression.objects.create(project=cls.other_project, name="Other Reg", owner=cls.user, is_active=True)

        # --- Runs (with varied timestamps) ---
        now = timezone.now()
        for i in range(5):
            RegressionRun.objects.create(
                regression=cls.reg1,
                run_number=i + 1,
                total_count=100,
                pass_count=90 - i * 5,
                fail_count=10 + i * 5,
                status=RunStatus.COMPLETED,
                created_at=now - timedelta(hours=i),
            )
        RegressionRun.objects.create(
            regression=cls.reg2,
            run_number=1,
            total_count=50,
            pass_count=45,
            fail_count=5,
            status=RunStatus.COMPLETED,
            created_at=now - timedelta(hours=1),
        )
        # Run from other project
        other_reg = Regression.objects.get(project=cls.other_project)
        RegressionRun.objects.create(
            regression=other_reg,
            run_number=1,
            total_count=30,
            pass_count=20,
            fail_count=10,
            status=RunStatus.COMPLETED,
        )

        # --- Milestones ---
        for i in range(3):
            Milestone.objects.create(
                project=cls.project,
                title=f"Milestone {i + 1}",
                status=MilestoneStatus.PLANNED,
                owner=cls.user,
                target_date=timezone.now().date() + timedelta(days=(i + 1) * 7),
            )

        # --- Failure signatures and results ---
        run = cls.reg1.runs.order_by("-created_at").first()
        cls.sig = FailureSignature.objects.create(
            regression_run=run,
            signature_title="Timeout",
            normalized_signature="timeout",
            signature_hash="ccc",
            category=FailureCategory.TIMEOUT,
            result_count=5,
        )
        cls.result = Result.objects.create(
            regression_run=run,
            test_name="test_timeout_case",
            status=ResultStatus.FAIL,
            failure_signature=cls.sig,
        )

    def setUp(self):
        self.client.login(username="projdash", password="password")

    # --- Basic rendering ---

    def test_returns_200(self):
        """Project dashboard page returns 200."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/project.html")

    def test_nonexistent_project_returns_404(self):
        """Requesting a non-existent project slug returns 404."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": "nonexistent"}))
        self.assertEqual(response.status_code, 404)

    # --- Context: project ---

    def test_context_project_is_correct(self):
        """Context 'project' is the requested project."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.context["project"], self.project)

    # --- Context: regressions (active only, limited to 10) ---

    def test_regressions_active_only(self):
        """Only active regressions are included."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        regs = list(response.context["regressions"])
        names = [r.name for r in regs]
        self.assertIn("Active Reg 1", names)
        self.assertIn("Active Reg 2", names)
        self.assertNotIn("Inactive Reg", names)

    def test_regressions_other_project_excluded(self):
        """Regressions from other projects are not included."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        reg_names = [r.name for r in response.context["regressions"]]
        self.assertNotIn("Other Reg", reg_names)

    def test_regressions_limited_to_10(self):
        """At most 10 regressions returned."""
        self.assertLessEqual(
            len(
                self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug})).context["regressions"]
            ),
            10,
        )

    # --- Context: latest_runs ---

    def test_latest_runs_project_only(self):
        """Only runs from the current project."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        runs = response.context["latest_runs"]
        for run in runs:
            self.assertEqual(run.regression.project, self.project)

    def test_latest_runs_ordered_by_created_at(self):
        """Runs ordered by created_at descending."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        runs = response.context["latest_runs"]
        created = [r.created_at for r in runs]
        self.assertEqual(created, sorted(created, reverse=True))

    def test_latest_runs_limited_to_10(self):
        """At most 10 latest runs."""
        self.assertLessEqual(
            len(
                self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug})).context["latest_runs"]
            ),
            10,
        )

    # --- Context: milestones ---

    def test_milestones_project_only(self):
        """Only milestones from the current project."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        for m in response.context["milestones"]:
            self.assertEqual(m.project, self.project)

    def test_milestones_limited_to_10(self):
        """At most 10 milestones."""
        self.assertLessEqual(
            len(
                self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug})).context["milestones"]
            ),
            10,
        )

    # --- Context: recent_signatures ---

    def test_recent_signatures_project_only(self):
        """Only failure signatures from the current project."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        for sig in response.context["recent_signatures"]:
            self.assertEqual(sig.regression_run.regression.project, self.project)

    def test_recent_signatures_limited_to_10(self):
        """At most 10 recent signatures."""
        self.assertLessEqual(
            len(
                self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug})).context[
                    "recent_signatures"
                ]
            ),
            10,
        )

    def test_recent_signatures_ordered_by_created_at(self):
        """Ordered by created_at descending."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        sigs = response.context["recent_signatures"]
        if len(sigs) > 1:
            created = [s.created_at for s in sigs]
            self.assertEqual(created, sorted(created, reverse=True))

    # --- Context: recent_failing ---

    def test_recent_failing_status_is_fail(self):
        """All recent failing results have status='fail'."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        for r in response.context["recent_failing"]:
            self.assertEqual(r.status, ResultStatus.FAIL)

    def test_recent_failing_project_only(self):
        """Only failing results from the current project."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        for r in response.context["recent_failing"]:
            self.assertEqual(r.regression_run.regression.project, self.project)

    def test_recent_failing_limited_to_10(self):
        """At most 10 recent failing results."""
        self.assertLessEqual(
            len(
                self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug})).context[
                    "recent_failing"
                ]
            ),
            10,
        )

    # --- Context: trend_runs ---

    def test_trend_runs_reversed_order(self):
        """trend_runs are the latest 10 runs reversed (oldest first)."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        trend = response.context["trend_runs"]
        if len(trend) > 1:
            created = [r.created_at for r in trend]
            self.assertEqual(created, sorted(created))

    def test_trend_runs_same_project(self):
        """All trend runs belong to the current project."""
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug}))
        for run in response.context["trend_runs"]:
            self.assertEqual(run.regression.project, self.project)

    def test_trend_runs_limited_to_10(self):
        """At most 10 trend runs."""
        self.assertLessEqual(
            len(
                self.client.get(reverse("project-dashboard", kwargs={"slug": self.project.slug})).context["trend_runs"]
            ),
            10,
        )

    # --- Empty project dashboard ---

    def test_empty_project_no_errors(self):
        """Dashboard for a project with no regressions/runs/milestones renders without errors."""
        empty_project = Project.objects.create(name="Empty Project", slug="empty-project")
        response = self.client.get(reverse("project-dashboard", kwargs={"slug": empty_project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"], empty_project)
        self.assertEqual(len(response.context["regressions"]), 0)
        self.assertEqual(len(response.context["latest_runs"]), 0)
        self.assertEqual(len(response.context["milestones"]), 0)
        self.assertEqual(len(response.context["recent_signatures"]), 0)
        self.assertEqual(len(response.context["recent_failing"]), 0)
        self.assertEqual(len(response.context["trend_runs"]), 0)
