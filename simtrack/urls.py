"""URL configuration for simtrack project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("projects/", include("projects.urls")),
    path("milestones/", include("milestones.urls")),
    path("regressions/", include("regressions.urls")),
    path("runs/", include("regressions.run_urls")),
    path("results/", include("results.urls")),
    path("failure-signatures/", include("results.signature_urls")),
]

if settings.SIMTRACK_ENABLE_ADMIN:
    urlpatterns.append(path("admin/", admin.site.urls))
