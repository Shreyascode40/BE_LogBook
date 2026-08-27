from __future__ import annotations

from rest_framework import serializers

from be_logbook.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "actor_role",
            "action",
            "entity",
            "object_id",
            "previous_state",
            "new_state",
            "ip_address",
            "user_agent",
            "timestamp",
        ]
