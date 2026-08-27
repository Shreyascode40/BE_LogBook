from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.users.models import User


class Notification(models.Model):
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    message = models.TextField()
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read"])]

    def __str__(self) -> str:
        return f"{self.notification_type}: {self.title}"

    def mark_read(self):
        from django.utils import timezone

        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save(update_fields=["read", "read_at"])
