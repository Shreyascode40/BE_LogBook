from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from be_logbook.audit.models import AuditLog
from be_logbook.audit.serializers import AuditLogSerializer
from be_logbook.utils.permissions import IsHOD


class AuditLogViewSet(ModelViewSet):
    queryset = AuditLog.objects.all().select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [IsHOD]
    http_method_names = ["get", "head", "options"]  # append-only; no writes
    filterset_fields = ["entity", "action", "actor_role"]
    search_fields = ["action", "entity"]
    ordering = ["-timestamp"]
