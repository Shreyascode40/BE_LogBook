from __future__ import annotations

from django.contrib import admin

from be_logbook.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity", "object_id", "actor", "actor_role", "timestamp"]
    list_filter = ["action", "entity", "actor_role"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]
