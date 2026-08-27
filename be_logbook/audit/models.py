from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.users.models import User


class AuditLog(models.Model):
    """Append-only academic audit trail. Never edited or deleted by users."""

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_role = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=60)
    entity = models.CharField(max_length=60)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    previous_state = models.TextField(blank=True, null=True)
    new_state = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity", "object_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor} @ {self.timestamp}"
