from __future__ import annotations

from django.contrib import admin

from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage
from be_logbook.workflow.models import StageDeadline
from be_logbook.workflow.models import StageDependency


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ["display_order", "code", "name", "required", "is_active", "reviewer_approval_required"]
    list_filter = ["required", "is_active"]
    ordering = ["display_order"]


admin.site.register(Section)
admin.site.register(StageDependency)
admin.site.register(StageDeadline)
