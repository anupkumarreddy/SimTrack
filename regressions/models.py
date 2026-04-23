
from django.db import models
from common.models import TimeStampedModel
from common.choices import RunStatus, TriggerType
from common.utils import calculate_pass_rate

class Regression(TimeStampedModel):
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='regressions')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    default_branch_name = models.CharField(max_length=255, blank=True)
    default_suite_name = models.CharField(max_length=255, blank=True)
    default_config_name = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class RegressionRun(TimeStampedModel):
    regression = models.ForeignKey(Regression, on_delete=models.CASCADE, related_name='runs')
    run_number = models.PositiveIntegerField()
    run_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.QUEUED)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.MANUAL)
    triggered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    branch_name = models.CharField(max_length=255, blank=True)
    suite_name = models.CharField(max_length=255, blank=True)
    config_name = models.CharField(max_length=255, blank=True)
    build_id = models.CharField(max_length=255, blank=True)
    git_commit = models.CharField(max_length=255, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_count = models.PositiveIntegerField(default=0)
    pass_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)
    timeout_count = models.PositiveIntegerField(default=0)
    killed_count = models.PositiveIntegerField(default=0)
    skip_count = models.PositiveIntegerField(default=0)
    unknown_count = models.PositiveIntegerField(default=0)
    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('regression', 'run_number')

    def __str__(self):
        return f"{self.regression.name} - Run #{self.run_number}"

    def save(self, *args, **kwargs):
        if self.total_count > 0:
            self.pass_rate = calculate_pass_rate(self.pass_count, self.total_count)
        else:
            self.pass_rate = 0.00
        super().save(*args, **kwargs)

    def duration_display(self):
        if self.start_time and self.end_time:
            diff = self.end_time - self.start_time
            total_seconds = int(diff.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "-"
