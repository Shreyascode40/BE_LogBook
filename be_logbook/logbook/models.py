from __future__ import annotations

import os

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.users.models import User


def _logbook_path(instance, filename):
    return f"logbooks/{instance.project_id}/{filename}"


class GeneratedLogBook(models.Model):
    STATUS = (
        ("READY", "Ready"),
        ("FAILED", "Failed"),
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="logbooks"
    )
    generated_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="logbooks_generated"
    )
    version = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to=_logbook_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="READY")
    generated_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Generated Log Book")
        verbose_name_plural = _("Generated Log Books")
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return f"LogBook {self.project_id} v{self.version} ({self.status})"
