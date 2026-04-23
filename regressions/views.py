
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Regression, RegressionRun
from .forms import RegressionForm, RegressionRunForm
from .services import get_next_run_number

class RegressionListView(ListView):
    model = Regression
    template_name = 'regressions/regression_list.html'
    context_object_name = 'regressions'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('project', 'created_by')
        project = self.request.GET.get('project')
        if project:
            qs = qs.filter(project_id=project)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from projects.models import Project
        ctx['project_list'] = Project.objects.all()
        return ctx

class RegressionDetailView(DetailView):
    model = Regression
    template_name = 'regressions/regression_detail.html'
    context_object_name = 'regression'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['runs'] = self.object.runs.all()[:20]
        ctx['latest_run'] = self.object.runs.first()
        return ctx

class RegressionCreateView(CreateView):
    model = Regression
    form_class = RegressionForm
    template_name = 'regressions/regression_form.html'
    success_url = reverse_lazy('regression-list')

class RegressionUpdateView(UpdateView):
    model = Regression
    form_class = RegressionForm
    template_name = 'regressions/regression_form.html'
    success_url = reverse_lazy('regression-list')

class RegressionDeleteView(DeleteView):
    model = Regression
    template_name = 'regressions/regression_confirm_delete.html'
    success_url = reverse_lazy('regression-list')

class RunListView(ListView):
    model = RegressionRun
    template_name = 'regressions/run_list.html'
    context_object_name = 'runs'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('regression__project')
        project = self.request.GET.get('project')
        regression = self.request.GET.get('regression')
        status = self.request.GET.get('status')
        trigger_type = self.request.GET.get('trigger_type')
        if project:
            qs = qs.filter(regression__project_id=project)
        if regression:
            qs = qs.filter(regression_id=regression)
        if status:
            qs = qs.filter(status=status)
        if trigger_type:
            qs = qs.filter(trigger_type=trigger_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from projects.models import Project
        from .models import Regression
        ctx['project_list'] = Project.objects.all()
        ctx['regression_list'] = Regression.objects.all()
        return ctx

class RunDetailView(DetailView):
    model = RegressionRun
    template_name = 'regressions/run_detail.html'
    context_object_name = 'run'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        run = self.object
        ctx['results'] = run.results.select_related('failure_signature').all()[:50]
        ctx['failure_signatures'] = run.failure_signatures.all()
        ctx['failed_results'] = run.results.filter(status='fail').select_related('failure_signature')
        ctx['status_counts'] = {
            'total': run.total_count,
            'pass': run.pass_count,
            'fail': run.fail_count,
            'timeout': run.timeout_count,
            'killed': run.killed_count,
            'skipped': run.skip_count,
            'unknown': run.unknown_count,
        }
        return ctx

class RunCreateView(CreateView):
    model = RegressionRun
    form_class = RegressionRunForm
    template_name = 'regressions/run_form.html'
    success_url = reverse_lazy('run-list')

    def form_valid(self, form):
        if not form.instance.run_number:
            form.instance.run_number = get_next_run_number(form.instance.regression)
        return super().form_valid(form)

class RunUpdateView(UpdateView):
    model = RegressionRun
    form_class = RegressionRunForm
    template_name = 'regressions/run_form.html'
    success_url = reverse_lazy('run-list')

class RunDeleteView(DeleteView):
    model = RegressionRun
    template_name = 'regressions/run_confirm_delete.html'
    success_url = reverse_lazy('run-list')
