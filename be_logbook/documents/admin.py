from __future__ import annotations

from django.contrib import admin

from be_logbook.documents.models import Document
from be_logbook.documents.models import DocumentVersion


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["document_type", "group", "uploaded_by", "version", "status", "created_at"]
    list_filter = ["document_type", "status"]


admin.site.register(DocumentVersion)
