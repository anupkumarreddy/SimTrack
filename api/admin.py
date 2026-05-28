from django.contrib import admin

from .models import ApiToken


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "scope_list", "is_active", "last_used_at", "created_at"]
    list_filter = ["is_active", "created_at", "last_used_at"]
    search_fields = ["name", "user__username", "user__email"]
    readonly_fields = ["token_hash", "last_used_at", "created_at", "updated_at"]

    def scope_list(self, obj):
        return ", ".join(obj.scopes or [])

    scope_list.short_description = "Scopes"
