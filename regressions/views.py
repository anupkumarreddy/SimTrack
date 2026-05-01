
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse
from calendar import Calendar
from datetime import date
from .models import Regression, RegressionRun
from .forms import RegressionForm, RegressionRunForm
from .services import get_next_run_number

class RegressionListView(ListView):
    model = Regression
    template_name = 'regressions/regression_list.html'
    context_object_name = 'regressions'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('project', 'owner')
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
        recent_runs = list(
            self.object.runs
            .select_related('triggered_by')
            .prefetch_related('results__failure_signature', 'failure_signatures')
            .all()[:25]
        )
        selected_month = self._selected_month(recent_runs)
        next_month = self._shift_month(selected_month, 1)
        previous_month = self._shift_month(selected_month, -1)
        calendar_runs = list(
            self.object.runs
            .select_related('triggered_by')
            .prefetch_related('results__failure_signature', 'failure_signatures')
            .filter(created_at__year=selected_month.year, created_at__month=selected_month.month)
            .order_by('created_at', 'run_number')
        )
        chart_runs = list(reversed(recent_runs))
        latest_run = recent_runs[0] if recent_runs else None
        payload_runs = {run.pk: run for run in recent_runs}
        payload_runs.update({run.pk: run for run in calendar_runs})
        ctx['runs'] = recent_runs
        ctx['latest_run'] = latest_run
        ctx['chart_runs'] = chart_runs
        ctx['chart_series'] = self._build_chart_series(chart_runs)
        ctx['chart_ticks'] = self._build_chart_ticks(chart_runs)
        ctx['calendar_runs'] = calendar_runs
        ctx['calendar_weeks'] = self._build_calendar_weeks(selected_month, calendar_runs)
        ctx['calendar_month_label'] = selected_month.strftime('%B %Y')
        ctx['previous_month'] = previous_month.strftime('%Y-%m')
        ctx['next_month'] = next_month.strftime('%Y-%m')
        ctx['run_payloads'] = [self._run_payload(run) for run in payload_runs.values()]
        return ctx

    def _selected_month(self, recent_runs):
        requested_month = self.request.GET.get('month', '')
        try:
            year, month = [int(part) for part in requested_month.split('-', 1)]
            return date(year, month, 1)
        except (TypeError, ValueError):
            if recent_runs:
                latest_date = recent_runs[0].created_at.date()
                return date(latest_date.year, latest_date.month, 1)
            today = date.today()
            return date(today.year, today.month, 1)

    def _shift_month(self, month_date, delta):
        month = month_date.month + delta
        year = month_date.year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        return date(year, month, 1)

    def _build_chart_series(self, runs):
        if not runs:
            return []
        series_defs = [
            ('Pass', '#16a34a', lambda run: float(run.pass_rate)),
            ('Fail', '#dc2626', self._fail_rate_number),
        ]
        series = []
        for label, color, getter in series_defs:
            points = self._build_chart_points(runs, getter)
            series.append({
                'label': label,
                'color': color,
                'path': self._build_chart_path(points),
                'points': points,
            })
        return series

    def _build_chart_points(self, runs, value_getter):
        width = 720
        height = 220
        padding_left = 44
        padding_right = 20
        padding_top = 18
        padding_bottom = 42
        plot_width = width - padding_left - padding_right
        plot_height = height - padding_top - padding_bottom
        denominator = max(len(runs) - 1, 1)
        points = []
        for index, run in enumerate(runs):
            value = value_getter(run)
            x = padding_left + (plot_width * index / denominator)
            y = padding_top + ((100 - value) * plot_height / 100)
            points.append({
                'x': round(x, 2),
                'y': round(y, 2),
                'value': f'{value:.2f}',
            })
        return points

    def _build_chart_path(self, points):
        if not points:
            return ''
        commands = [f"M {points[0]['x']} {points[0]['y']}"]
        commands.extend(f"L {point['x']} {point['y']}" for point in points[1:])
        return ' '.join(commands)

    def _build_chart_ticks(self, runs):
        if not runs:
            return []
        points = self._build_chart_points(runs, lambda run: 0)
        ticks = []
        previous_label = None
        for index, run in enumerate(runs):
            label = run.created_at.strftime('%b %-d')
            if label == previous_label:
                label = run.created_at.strftime('%H:%M')
            ticks.append({
                'x': points[index]['x'],
                'label': label,
            })
            previous_label = label
        return ticks

    def _build_calendar_weeks(self, selected_month, runs):
        runs_by_date = {}
        for run in runs:
            run.calendar_fail_rate = self._fail_rate(run)
            runs_by_date.setdefault(run.created_at.date(), []).append(run)

        weeks = []
        for week in Calendar(firstweekday=6).monthdatescalendar(selected_month.year, selected_month.month):
            week_days = []
            for day in week:
                week_days.append({
                    'date': day,
                    'in_month': day.month == selected_month.month,
                    'runs': runs_by_date.get(day, []),
                })
            weeks.append(week_days)
        return weeks

    def _fail_rate(self, run):
        if run.total_count <= 0:
            return '0.00'
        return f'{(run.fail_count * 100 / run.total_count):.2f}'

    def _rate_number(self, count, total):
        if total <= 0:
            return 0.0
        return count * 100 / total

    def _fail_rate_number(self, run):
        return self._rate_number(run.fail_count, run.total_count)

    def _timeout_rate_number(self, run):
        return self._rate_number(run.timeout_count, run.total_count)

    def _killed_rate_number(self, run):
        return self._rate_number(run.killed_count, run.total_count)

    def _skipped_rate_number(self, run):
        return self._rate_number(run.skip_count, run.total_count)

    def _unknown_rate_number(self, run):
        return self._rate_number(run.unknown_count, run.total_count)

    def _run_payload(self, run):
        results = list(run.results.select_related('failure_signature').all()[:50])
        failed_results = [result for result in results if result.status == 'fail']
        signatures = list(run.failure_signatures.all())
        return {
            'id': run.pk,
            'run_number': run.run_number,
            'run_name': run.run_name or '',
            'status': run.status,
            'status_display': run.get_status_display(),
            'trigger_type': run.get_trigger_type_display(),
            'triggered_by': str(run.triggered_by) if run.triggered_by else '—',
            'branch_name': run.branch_name or '—',
            'suite_name': run.suite_name or '—',
            'config_name': run.config_name or '—',
            'build_id': run.build_id or '—',
            'git_commit': run.git_commit or '—',
            'duration': run.duration_display(),
            'created_at': run.created_at.strftime('%Y-%m-%d %H:%M'),
            'date': run.created_at.strftime('%Y-%m-%d'),
            'pass_rate': str(run.pass_rate),
            'fail_rate': self._fail_rate(run),
            'total_count': run.total_count,
            'pass_count': run.pass_count,
            'fail_count': run.fail_count,
            'timeout_count': run.timeout_count,
            'killed_count': run.killed_count,
            'skip_count': run.skip_count,
            'unknown_count': run.unknown_count,
            'notes': run.notes,
            'detail_url': reverse('run-detail', kwargs={'pk': run.pk}),
            'results_url': f"{reverse('result-list')}?run={run.pk}",
            'results': [self._result_payload(result) for result in results],
            'failed_results': [self._result_payload(result) for result in failed_results],
            'failure_signatures': [self._signature_payload(signature) for signature in signatures],
        }

    def _result_payload(self, result):
        return {
            'id': result.pk,
            'test_name': result.test_name,
            'status': result.status,
            'status_display': result.get_status_display(),
            'seed': result.seed or '—',
            'duration_seconds': str(result.duration_seconds) if result.duration_seconds is not None else '—',
            'machine_name': result.machine_name or '—',
            'error_message': result.error_message or '—',
            'signature': result.failure_signature.signature_title if result.failure_signature else '—',
            'signature_url': reverse('failure-signature-detail', kwargs={'pk': result.failure_signature.pk}) if result.failure_signature else '',
            'detail_url': reverse('result-detail', kwargs={'pk': result.pk}),
        }

    def _signature_payload(self, signature):
        return {
            'id': signature.pk,
            'title': signature.signature_title,
            'category': signature.get_category_display(),
            'result_count': signature.result_count,
            'is_known_issue': 'Yes' if signature.is_known_issue else 'No',
            'is_infra_issue': 'Yes' if signature.is_infra_issue else 'No',
            'detail_url': reverse('failure-signature-detail', kwargs={'pk': signature.pk}),
        }

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
