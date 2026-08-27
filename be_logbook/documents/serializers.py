from __future__ import annotations

from rest_framework import serializers

from be_logbook.documents.models import Document
from be_logbook.documents.models import DocumentType
from be_logbook.documents.models import DocumentVersion


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(
        source="uploaded_by.email", read_only=True
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "document_type",
            "group",
            "project",
            "stage",
            "owner",
            "uploaded_by",
            "uploaded_by_email",
            "version",
            "original_filename",
            "file_size",
            "mime_type",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uploaded_by",
            "version",
            "file_size",
            "mime_type",
            "status",
            "checksum",
        ]


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    project_id = serializers.IntegerField(required=False, allow_null=True)
    stage_id = serializers.IntegerField(required=False, allow_null=True)
    owner_id = serializers.IntegerField(required=False, allow_null=True)


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "version",
            "original_filename",
            "file_size",
            "mime_type",
            "uploaded_by",
            "created_at",
        ]
