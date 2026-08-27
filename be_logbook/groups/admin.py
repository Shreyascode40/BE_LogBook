from __future__ import annotations

from django.contrib import admin

from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import GuideAssignment
from be_logbook.groups.models import ProjectGroup


@admin.register(ProjectGroup)
class ProjectGroupAdmin(admin.ModelAdmin):
    list_display = [
        "group_number",
        "academic_year",
        "department",
        "status",
        "current_stage",
    ]
    list_filter = ["academic_year", "department", "status"]
    search_fields = ["group_number"]


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ["group", "student", "status", "designation", "join_date"]
    list_filter = ["status"]


@admin.register(GuideAssignment)
class GuideAssignmentAdmin(admin.ModelAdmin):
    list_display = ["group", "faculty", "assigned_at", "is_active"]
    list_filter = ["is_active"]
