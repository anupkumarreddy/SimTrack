
from django.views.generic import ListView, DetailView
from .models import Result, FailureSignature

class ResultListView(ListView):
    model = Result
    template_name = 'results/result_list.html'
    context_object_name = 'results'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related('regression_run__regression__project', 'failure_signature')
        project = self.request.GET.get('project')
        regression = self.request.GET.get('regression')
        run = self.request.GET.get('run')
        status = self.request.GET.get('status')
        test_name = self.request.GET.get('test_name')
        signature = self.request.GET.get('signature')
        if project:
            qs = qs.filter(regression_run__regression__project_id=project)
        if regression:
            qs = qs.filter(regression_run__regression_id=regression)
        if run:
            qs = qs.filter(regression_run_id=run)
        if status:
            qs = qs.filter(status=status)
        if test_name:
            qs = qs.filter(test_name__icontains=test_name)
        if signature:
            qs = qs.filter(failure_signature_id=signature)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from projects.models import Project
        from regressions.models import Regression, RegressionRun
        ctx['project_list'] = Project.objects.all()
        ctx['regression_list'] = Regression.objects.all()
        ctx['run_list'] = RegressionRun.objects.all()
        ctx['signature_list'] = FailureSignature.objects.all()
        return ctx

class ResultDetailView(DetailView):
    model = Result
    template_name = 'results/result_detail.html'
    context_object_name = 'result'

class FailureSignatureDetailView(DetailView):
    model = FailureSignature
    template_name = 'results/failure_signature_detail.html'
    context_object_name = 'signature'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['results'] = self.object.results.all()[:50]
        return ctx
