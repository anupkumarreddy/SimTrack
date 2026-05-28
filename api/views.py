from django.utils.dateparse import parse_datetime
from rest_framework import exceptions, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result

from .permissions import HasIngestScope, HasReadScope, HasWriteScope
from .serializers import (
    FailureSignatureSerializer,
    IngestRunPayloadSerializer,
    ProjectSerializer,
    RegressionRunSerializer,
    RegressionSerializer,
    ResultSerializer,
)
from .services import ingest_run


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class FilteredReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasReadScope]
    filter_map = {}

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {}
        for query_param, lookup in self.filter_map.items():
            value = self.request.query_params.get(query_param)
            if value not in (None, ""):
                filters[lookup] = value

        created_after = self._parse_datetime_param("created_after")
        created_before = self._parse_datetime_param("created_before")
        if created_after:
            filters["created_at__gte"] = created_after
        if created_before:
            filters["created_at__lte"] = created_before

        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    def _parse_datetime_param(self, name):
        value = self.request.query_params.get(name)
        if not value:
            return None
        return parse_datetime(value)


class ScopedModelViewSet(FilteredReadOnlyModelViewSet, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]
    write_actions = {"create", "update", "partial_update", "destroy"}

    def get_permissions(self):
        permission_classes = [IsAuthenticated]
        if self.action in self.write_actions:
            permission_classes.append(HasWriteScope)
        else:
            permission_classes.append(HasReadScope)
        return [permission() for permission in permission_classes]


class ProjectViewSet(ScopedModelViewSet):
    queryset = Project.objects.select_related("category", "owner").all()
    serializer_class = ProjectSerializer
    filter_map = {
        "status": "status",
    }


class RegressionViewSet(ScopedModelViewSet):
    queryset = Regression.objects.select_related("project", "owner").all()
    serializer_class = RegressionSerializer
    filter_map = {
        "project": "project_id",
    }


class RegressionRunViewSet(ScopedModelViewSet):
    queryset = RegressionRun.objects.select_related("regression__project", "triggered_by").all()
    serializer_class = RegressionRunSerializer
    filter_map = {
        "project": "regression__project_id",
        "regression": "regression_id",
        "status": "status",
        "branch": "branch_name",
        "suite": "suite_name",
    }

    def perform_create(self, serializer):
        serializer.save(triggered_by=self.request.user)


class ResultViewSet(FilteredReadOnlyModelViewSet):
    queryset = Result.objects.select_related(
        "regression_run__regression__project",
        "failure_signature",
    ).all()
    serializer_class = ResultSerializer
    filter_map = {
        "project": "regression_run__regression__project_id",
        "regression": "regression_run__regression_id",
        "run": "regression_run_id",
        "status": "status",
    }


class FailureSignatureViewSet(FilteredReadOnlyModelViewSet):
    queryset = FailureSignature.objects.select_related("regression_run__regression__project").all()
    serializer_class = FailureSignatureSerializer
    filter_map = {
        "project": "regression_run__regression__project_id",
        "regression": "regression_run__regression_id",
        "run": "regression_run_id",
    }


class IngestRunView(APIView):
    permission_classes = [IsAuthenticated, HasIngestScope]

    def post(self, request):
        serializer = IngestRunPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = ingest_run(serializer.validated_data, request.user)
        except ValueError as exc:
            raise exceptions.ValidationError({"non_field_errors": [str(exc)]}) from exc

        return Response(
            {
                "project": ProjectSerializer(result["project"]).data,
                "regression": RegressionSerializer(result["regression"]).data,
                "run": RegressionRunSerializer(result["run"]).data,
                "created": result["created"],
                "result_count": result["result_count"],
            },
            status=status.HTTP_201_CREATED if result["created"]["run"] else status.HTTP_200_OK,
        )
