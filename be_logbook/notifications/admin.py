from __future__ import annotations

from django.contrib import admin

from be_logbook.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "notification_type", "title", "read", "created_at"]
    list_filter = ["notification_type", "read"]
