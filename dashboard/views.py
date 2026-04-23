
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result
from milestones.models import Milestone

class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_projects'] = Project.objects.filter(is_active=True).count()
        ctx['active_regressions'] = Regression.objects.filter(is_active=True).count()
        ctx['recent_runs'] = RegressionRun.objects.select_related('regression__project').order_by('-created_at')[:10]
        ctx['recent_failed_runs'] = RegressionRun.objects.filter(status='failed').select_related('regression__project').order_by('-created_at')[:10]
        ctx['milestones'] = Milestone.objects.select_related('project').order_by('-created_at')[:10]
        ctx['top_signatures'] = FailureSignature.objects.select_related('regression_run__regression__project').order_by('-result_count')[:10]
        return ctx

class ProjectDashboardView(TemplateView):
    template_name = 'dashboard/project.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, slug=self.kwargs['slug'])
        ctx['project'] = project
        ctx['regressions'] = project.regressions.filter(is_active=True)[:10]
        ctx['latest_runs'] = RegressionRun.objects.filter(regression__project=project).select_related('regression').order_by('-created_at')[:10]
        ctx['milestones'] = project.milestones.order_by('-target_date')[:10]
        ctx['recent_signatures'] = FailureSignature.objects.filter(regression_run__regression__project=project).select_related('regression_run').order_by('-created_at')[:10]
        ctx['recent_failing'] = Result.objects.filter(regression_run__regression__project=project, status='fail').select_related('regression_run', 'failure_signature').order_by('-created_at')[:10]
        # Simple trend: pass/fail counts from latest 10 runs
        runs = RegressionRun.objects.filter(regression__project=project).order_by('-created_at')[:10]
        ctx['trend_runs'] = list(reversed(runs))
        return ctx
