from django.db import models

from common.choices import FailureCategory, ResultStatus
from common.models import TimeStampedModel


class FailureSignature(TimeStampedModel):
    regression_run = models.ForeignKey(
        "regressions.RegressionRun", on_delete=models.CASCADE, related_name="failure_signatures"
    )
    signature_title = models.CharField(max_length=500)
    normalized_signature = models.TextField(blank=True)
    signature_hash = models.CharField(max_length=64)
    category = models.CharField(max_length=20, choices=FailureCategory.choices, default=FailureCategory.UNKNOWN)
    description = models.TextField(blank=True)
    result_count = models.PositiveIntegerField(default=0)
    is_known_issue = models.BooleanField(default=False)
    is_infra_issue = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("regression_run", "signature_hash")
        ordering = ["-result_count"]

    def __str__(self):
        return self.signature_title


class Result(TimeStampedModel):
    regression_run = models.ForeignKey("regressions.RegressionRun", on_delete=models.CASCADE, related_name="results")
    failure_signature = models.ForeignKey(
        FailureSignature, on_delete=models.SET_NULL, null=True, blank=True, related_name="results"
    )
    test_name = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=ResultStatus.choices, default=ResultStatus.UNKNOWN)
    seed = models.CharField(max_length=100, blank=True)
    duration_seconds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    machine_name = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    log_path = models.CharField(max_length=500, blank=True)
    wave_path = models.CharField(max_length=500, blank=True)
    artifact_path = models.CharField(max_length=500, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    rerun_index = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["regression_run", "status"]),
            models.Index(fields=["regression_run", "test_name"]),
            models.Index(fields=["regression_run"]),
            models.Index(fields=["status"]),
            models.Index(fields=["test_name"]),
            models.Index(fields=["failure_signature"]),
        ]

    def __str__(self):
        return self.test_name
