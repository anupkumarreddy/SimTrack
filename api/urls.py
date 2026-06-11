from django.urls import include, path
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONOpenAPIRenderer
from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view

from .permissions import HasReadScope
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
    path(
        "schema/",
        get_schema_view(
            title="SimTrack API",
            description="REST API for SimTrack project, regression, run, result, and ingestion access.",
            version="1.1.0",
            permission_classes=[IsAuthenticated, HasReadScope],
            renderer_classes=[JSONOpenAPIRenderer],
        ),
        name="api-schema",
    ),
    path("ingest/run/", IngestRunView.as_view(), name="api-ingest-run"),
    path("", include(router.urls)),
]
