from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FailureSignatureViewSet,
    HealthView,
    IngestRunView,
    ProjectViewSet,
    RegressionRunViewSet,
    RegressionViewSet,
    ResultViewSet,
)

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="api-project")
router.register("regressions", RegressionViewSet, basename="api-regression")
router.register("runs", RegressionRunViewSet, basename="api-run")
router.register("results", ResultViewSet, basename="api-result")
router.register("failure-signatures", FailureSignatureViewSet, basename="api-failure-signature")

urlpatterns = [
    path("health/", HealthView.as_view(), name="api-health"),
    path("ingest/run/", IngestRunView.as_view(), name="api-ingest-run"),
    path("", include(router.urls)),
]
