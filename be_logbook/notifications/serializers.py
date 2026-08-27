from __future__ import annotations

from rest_framework import serializers

from be_logbook.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "read",
            "read_at",
            "created_at",
        ]
