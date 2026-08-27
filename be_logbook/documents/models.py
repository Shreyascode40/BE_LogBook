from __future__ import annotations

import hashlib
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from be_logbook.users.models import User


def _doc_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    unique = uuid.uuid4().hex
    group_id = getattr(instance, "group_id", None)
    if group_id is None and hasattr(instance, "document"):
        group_id = instance.document.group_id
    return f"docs/{group_id or 'user'}/{unique}{ext}"


class DocumentType(models.TextChoices):
    PHOTO = "PHOTO", "Student Photograph"
    SYNOPSIS = "SYNOPSIS", "Synopsis"
    REPORT = "REPORT", "Project Report"
    UML = "UML", "UML Diagram"
    PAPER = "PAPER", "Research Paper"
    CERTIFICATE = "CERTIFICATE", "Certificate"
    COMPETITION_CERT = "COMPETITION_CERT", "Competition Certificate"
    SPONSORSHIP = "SPONSORSHIP", "Sponsorship / Completion Letter"
    PPT = "PPT", "Presentation (PPT)"
    CODE = "CODE", "Code / Archive"
    OTHER = "OTHER", "Other"


class DocumentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    REPLACED = "REPLACED", "Replaced"
    DELETED = "DELETED", "Deleted"


class Document(models.Model):
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    group = models.ForeignKey(
        "groups.ProjectGroup",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    stage = models.ForeignKey(
        "workflow.Stage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="documents_owned",
        null=True,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="documents_uploaded"
    )
    version = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to=_doc_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.document_type} v{self.version} ({self.original_filename})"

    @property
    def file_path(self):
        return os.path.join(settings.PRIVATE_MEDIA_ROOT, self.file.name)


class DocumentVersion(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.PositiveIntegerField()
    file = models.FileField(upload_to=_doc_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="document_versions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Document Version")
        verbose_name_plural = _("Document Versions")
        ordering = ["document", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version"], name="uniq_document_version"
            )
        ]

    def __str__(self) -> str:
        return f"{self.document} v{self.version}"


def compute_checksum(file_obj) -> str:
    h = hashlib.sha256()
    for chunk in file_obj.chunks():
        h.update(chunk)
    return h.hexdigest()
