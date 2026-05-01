from django.contrib import admin

from .models import FailureSignature, Result


@admin.register(FailureSignature)
class FailureSignatureAdmin(admin.ModelAdmin):
    list_display = ["regression_run", "signature_title", "category", "result_count", "is_known_issue", "is_infra_issue"]
    list_filter = ["category", "is_known_issue", "is_infra_issue"]
    search_fields = ["signature_title", "normalized_signature"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ["regression_run", "test_name", "status", "duration_seconds", "machine_name"]
    list_filter = ["status"]
    search_fields = ["test_name", "error_message"]
    readonly_fields = ["created_at", "updated_at"]
