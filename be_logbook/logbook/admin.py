from __future__ import annotations

from django.contrib import admin

from be_logbook.logbook.models import GeneratedLogBook


@admin.register(GeneratedLogBook)
class GeneratedLogBookAdmin(admin.ModelAdmin):
    list_display = ["project", "generated_by", "version", "status", "generated_at"]
    list_filter = ["status"]
