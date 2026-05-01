from django.db import models


class ProjectStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class MilestoneStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    COMPLETED = "completed", "Completed"
    DELAYED = "delayed", "Delayed"


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    ENGINEER = "engineer", "Engineer"
    VIEWER = "viewer", "Viewer"


class RunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"
    ABORTED = "aborted", "Aborted"


class TriggerType(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULED = "scheduled", "Scheduled"
    CI = "ci", "CI"
    API = "api", "API"


class FailureCategory(models.TextChoices):
    DESIGN = "design", "Design"
    CONFIG = "config", "Config"
    INFRA = "infra", "Infrastructure"
    TIMEOUT = "timeout", "Timeout"
    UNKNOWN = "unknown", "Unknown"


class ResultStatus(models.TextChoices):
    PASS = "pass", "Pass"
    FAIL = "fail", "Fail"
    TIMEOUT = "timeout", "Timeout"
    KILLED = "killed", "Killed"
    SKIPPED = "skipped", "Skipped"
    RUNNING = "running", "Running"
    UNKNOWN = "unknown", "Unknown"
