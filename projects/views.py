
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Project
from .forms import ProjectForm

class ProjectListView(ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'owner')
        status = self.request.GET.get('status')
        q = self.request.GET.get('q')
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        ctx['regressions'] = project.regressions.select_related('created_by')[:10]
        from regressions.models import RegressionRun
        ctx['recent_runs'] = RegressionRun.objects.filter(regression__project=project).select_related('regression').order_by('-created_at')[:10]
        ctx['milestones'] = project.milestones.order_by('-target_date')[:10]
        return ctx

class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('project-list')

class ProjectUpdateView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'slug': self.object.slug})

class ProjectDeleteView(DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('project-list')
