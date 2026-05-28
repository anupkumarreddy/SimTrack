from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result

from .permissions import HasIngestScope, HasReadScope
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


class ProjectViewSet(FilteredReadOnlyModelViewSet):
    queryset = Project.objects.select_related("category", "owner").all()
    serializer_class = ProjectSerializer
    filter_map = {
        "status": "status",
    }


class RegressionViewSet(FilteredReadOnlyModelViewSet):
    queryset = Regression.objects.select_related("project", "owner").all()
    serializer_class = RegressionSerializer
    filter_map = {
        "project": "project_id",
    }


class RegressionRunViewSet(FilteredReadOnlyModelViewSet):
    queryset = RegressionRun.objects.select_related("regression__project", "triggered_by").all()
    serializer_class = RegressionRunSerializer
    filter_map = {
        "project": "regression__project_id",
        "regression": "regression_id",
        "status": "status",
        "branch": "branch_name",
        "suite": "suite_name",
    }


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
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

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
