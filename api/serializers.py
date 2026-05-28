from rest_framework import serializers

from projects.models import Project, ProjectCategory
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result


class ProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ProjectSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "category_name",
            "owner",
            "owner_username",
            "status",
            "repository_url",
            "is_active",
            "created_at",
            "updated_at",
        ]


class RegressionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Regression
        fields = [
            "id",
            "project",
            "project_name",
            "name",
            "description",
            "is_active",
            "owner",
            "owner_username",
            "default_branch_name",
            "default_suite_name",
            "default_config_name",
            "metadata",
            "created_at",
            "updated_at",
        ]


class RegressionRunSerializer(serializers.ModelSerializer):
    regression_name = serializers.CharField(source="regression.name", read_only=True)
    project = serializers.IntegerField(source="regression.project_id", read_only=True)
    project_name = serializers.CharField(source="regression.project.name", read_only=True)
    triggered_by_username = serializers.CharField(source="triggered_by.username", read_only=True)

    class Meta:
        model = RegressionRun
        fields = [
            "id",
            "regression",
            "regression_name",
            "project",
            "project_name",
            "run_number",
            "run_name",
            "status",
            "trigger_type",
            "triggered_by",
            "triggered_by_username",
            "branch_name",
            "suite_name",
            "config_name",
            "build_id",
            "git_commit",
            "start_time",
            "end_time",
            "total_count",
            "pass_count",
            "fail_count",
            "timeout_count",
            "killed_count",
            "skip_count",
            "unknown_count",
            "pass_rate",
            "metadata",
            "notes",
            "created_at",
            "updated_at",
        ]


class FailureSignatureSerializer(serializers.ModelSerializer):
    regression = serializers.IntegerField(source="regression_run.regression_id", read_only=True)
    project = serializers.IntegerField(source="regression_run.regression.project_id", read_only=True)

    class Meta:
        model = FailureSignature
        fields = [
            "id",
            "regression_run",
            "regression",
            "project",
            "signature_title",
            "normalized_signature",
            "signature_hash",
            "category",
            "description",
            "result_count",
            "is_known_issue",
            "is_infra_issue",
            "metadata",
            "created_at",
            "updated_at",
        ]


class ResultSerializer(serializers.ModelSerializer):
    regression = serializers.IntegerField(source="regression_run.regression_id", read_only=True)
    project = serializers.IntegerField(source="regression_run.regression.project_id", read_only=True)
    failure_signature_title = serializers.CharField(source="failure_signature.signature_title", read_only=True)

    class Meta:
        model = Result
        fields = [
            "id",
            "regression_run",
            "regression",
            "project",
            "failure_signature",
            "failure_signature_title",
            "test_name",
            "status",
            "seed",
            "duration_seconds",
            "machine_name",
            "error_message",
            "log_path",
            "wave_path",
            "artifact_path",
            "started_at",
            "ended_at",
            "rerun_index",
            "metadata",
            "created_at",
            "updated_at",
        ]


class IngestProjectSerializer(serializers.Serializer):
    slug = serializers.SlugField(required=False, allow_blank=True)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    repository_url = serializers.URLField(required=False, allow_blank=True)


class IngestRegressionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    branch_name = serializers.CharField(required=False, allow_blank=True)
    suite_name = serializers.CharField(required=False, allow_blank=True)
    config_name = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class IngestRunSerializer(serializers.Serializer):
    run_number = serializers.IntegerField(required=False, min_value=1)
    run_name = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    trigger_type = serializers.CharField(required=False, allow_blank=True)
    branch_name = serializers.CharField(required=False, allow_blank=True)
    suite_name = serializers.CharField(required=False, allow_blank=True)
    config_name = serializers.CharField(required=False, allow_blank=True)
    build_id = serializers.CharField(required=False, allow_blank=True)
    git_commit = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class IngestFailureSignatureSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    category = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    is_known_issue = serializers.BooleanField(required=False, default=False)
    is_infra_issue = serializers.BooleanField(required=False, default=False)


class IngestResultSerializer(serializers.Serializer):
    test_name = serializers.CharField(max_length=500)
    status = serializers.CharField(required=False, allow_blank=True)
    seed = serializers.CharField(required=False, allow_blank=True)
    duration_seconds = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True)
    machine_name = serializers.CharField(required=False, allow_blank=True)
    error_message = serializers.CharField(required=False, allow_blank=True)
    log_path = serializers.CharField(required=False, allow_blank=True)
    wave_path = serializers.CharField(required=False, allow_blank=True)
    artifact_path = serializers.CharField(required=False, allow_blank=True)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    ended_at = serializers.DateTimeField(required=False, allow_null=True)
    rerun_index = serializers.IntegerField(required=False, min_value=0)
    metadata = serializers.JSONField(required=False)
    failure_signature = IngestFailureSignatureSerializer(required=False)


class IngestRunPayloadSerializer(serializers.Serializer):
    project = IngestProjectSerializer()
    regression = IngestRegressionSerializer()
    run = IngestRunSerializer()
    results = IngestResultSerializer(many=True, required=False)
