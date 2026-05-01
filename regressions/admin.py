from django.contrib import admin

from .models import Regression, RegressionRun


@admin.register(Regression)
class RegressionAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "is_active", "owner", "created_at"]
    list_filter = ["is_active", "project"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RegressionRun)
class RegressionRunAdmin(admin.ModelAdmin):
    list_display = ["regression", "run_number", "status", "pass_rate", "start_time", "created_at"]
    list_filter = ["status", "trigger_type", "regression__project"]
    search_fields = ["run_name", "build_id", "git_commit"]
    readonly_fields = ["created_at", "updated_at", "pass_rate"]
    date_hierarchy = "created_at"
