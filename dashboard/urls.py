from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard-alt"),
    path("dashboard/project/<slug:slug>/", views.ProjectDashboardView.as_view(), name="project-dashboard"),
]
