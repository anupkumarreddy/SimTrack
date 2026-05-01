
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Milestone, MilestoneUpdate
from .forms import MilestoneForm, MilestoneUpdateForm
from common.mixins import StaffRequiredMixin

class MilestoneListView(ListView):
    model = Milestone
    template_name = 'milestones/milestone_list.html'
    context_object_name = 'milestones'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.GET.get('project')
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        if project:
            qs = qs.filter(project_id=project)
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from projects.models import Project
        ctx['project_list'] = Project.objects.all()
        return ctx

class MilestoneDetailView(DetailView):
    model = Milestone
    template_name = 'milestones/milestone_detail.html'
    context_object_name = 'milestone'

class MilestoneCreateView(StaffRequiredMixin, CreateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'milestones/milestone_form.html'
    success_url = reverse_lazy('milestone-list')

class MilestoneUpdateView(StaffRequiredMixin, UpdateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'milestones/milestone_form.html'

    def get_success_url(self):
        return reverse_lazy('milestone-detail', kwargs={'pk': self.object.pk})

class MilestoneDeleteView(StaffRequiredMixin, DeleteView):
    model = Milestone
    template_name = 'milestones/milestone_confirm_delete.html'
    success_url = reverse_lazy('milestone-list')

class MilestoneUpdateCreateView(StaffRequiredMixin, CreateView):
    model = MilestoneUpdate
    form_class = MilestoneUpdateForm
    template_name = 'milestones/milestoneupdate_form.html'

    def form_valid(self, form):
        milestone = get_object_or_404(Milestone, pk=self.kwargs['pk'])
        form.instance.milestone = milestone
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('milestone-detail', kwargs={'pk': self.kwargs['pk']})
