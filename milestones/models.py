from django.db import models

from common.choices import MilestoneStatus, Priority
from common.models import TimeStampedModel


class Milestone(TimeStampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PLANNED)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_milestones"
    )
    target_date = models.DateField(null=True, blank=True)
    completion_percentage = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-target_date", "-created_at"]

    def __str__(self):
        return self.title


class MilestoneUpdate(TimeStampedModel):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="updates")
    comment = models.TextField()
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Update on {self.milestone}"
