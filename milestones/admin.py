
from django.contrib import admin
from .models import Milestone, MilestoneUpdate

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'priority', 'target_date', 'completion_percentage']
    list_filter = ['status', 'priority', 'project']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(MilestoneUpdate)
class MilestoneUpdateAdmin(admin.ModelAdmin):
    list_display = ['milestone', 'updated_by', 'created_at']
    list_filter = ['milestone__project']
    search_fields = ['comment']
    readonly_fields = ['created_at', 'updated_at']
