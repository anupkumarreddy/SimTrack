from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from common.choices import MilestoneStatus
from milestones.models import Milestone
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_projects"] = Project.objects.count()
        ctx["total_regressions"] = Regression.objects.count()
        ctx["total_runs"] = RegressionRun.objects.count()
        ctx["total_milestones"] = Milestone.objects.count()

        project_rows = []
        for project in (
            Project.objects.select_related("owner")
            .annotate(
                total_tests=Sum("regressions__runs__total_count"),
                total_passed=Sum("regressions__runs__pass_count"),
                run_count=Count("regressions__runs", distinct=True),
                regression_count=Count("regressions", distinct=True),
                milestone_count=Count("milestones", distinct=True),
                completed_milestone_count=Count(
                    "milestones", filter=Q(milestones__status=MilestoneStatus.COMPLETED), distinct=True
                ),
            )
            .order_by("name")
        ):
            total_tests = project.total_tests or 0
            total_passed = project.total_passed or 0
            pass_rate = (total_passed * 100 / total_tests) if total_tests else 0
            milestone_count = project.milestone_count or 0
            completed_milestone_count = project.completed_milestone_count or 0
            milestone_rate = (completed_milestone_count * 100 / milestone_count) if milestone_count else 0
            project_rows.append(
                {
                    "project": project,
                    "pass_rate": f"{pass_rate:.2f}",
                    "pass_rate_value": pass_rate,
                    "run_count": project.run_count,
                    "regression_count": project.regression_count,
                    "milestone_count": milestone_count,
                    "completed_milestone_count": completed_milestone_count,
                    "milestone_rate": f"{milestone_rate:.0f}",
                }
            )

        regression_rows = []
        for regression in Regression.objects.select_related("project", "owner").annotate(
            total_tests=Sum("runs__total_count"),
            total_passed=Sum("runs__pass_count"),
            total_failed=Sum("runs__fail_count"),
            run_count=Count("runs", distinct=True),
        ):
            total_tests = regression.total_tests or 0
            pass_rate = ((regression.total_passed or 0) * 100 / total_tests) if total_tests else 0
            fail_rate = ((regression.total_failed or 0) * 100 / total_tests) if total_tests else 0
            regression_rows.append(
                {
                    "regression": regression,
                    "pass_rate": f"{pass_rate:.2f}",
                    "fail_rate": f"{fail_rate:.2f}",
                    "pass_rate_value": pass_rate,
                    "fail_rate_value": fail_rate,
                    "run_count": regression.run_count,
                }
            )

        ctx["project_rows"] = project_rows
        ctx["top_failing_regressions"] = sorted(regression_rows, key=lambda row: row["fail_rate_value"], reverse=True)[
            :5
        ]
        ctx["top_passing_regressions"] = sorted(regression_rows, key=lambda row: row["pass_rate_value"], reverse=True)[
            :5
        ]
        ctx["upcoming_milestones"] = (
            Milestone.objects.select_related("project", "owner")
            .filter(target_date__gte=timezone.now().date())
            .order_by("target_date", "project__name")[:5]
        )
        ctx["top_signatures"] = FailureSignature.objects.select_related("regression_run__regression__project").order_by(
            "-result_count"
        )[:5]
        return ctx


class ProjectDashboardView(TemplateView):
    template_name = "dashboard/project.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, slug=self.kwargs["slug"])
        ctx["project"] = project
        ctx["regressions"] = project.regressions.filter(is_active=True)[:10]
        ctx["latest_runs"] = (
            RegressionRun.objects.filter(regression__project=project)
            .select_related("regression")
            .order_by("-created_at")[:10]
        )
        ctx["milestones"] = project.milestones.order_by("-target_date")[:10]
        ctx["recent_signatures"] = (
            FailureSignature.objects.filter(regression_run__regression__project=project)
            .select_related("regression_run")
            .order_by("-created_at")[:10]
        )
        ctx["recent_failing"] = (
            Result.objects.filter(regression_run__regression__project=project, status="fail")
            .select_related("regression_run", "failure_signature")
            .order_by("-created_at")[:10]
        )
        # Simple trend: pass/fail counts from latest 10 runs
        runs = RegressionRun.objects.filter(regression__project=project).order_by("-created_at")[:10]
        ctx["trend_runs"] = list(reversed(runs))
        return ctx
