from __future__ import annotations

from rest_framework import serializers

from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage
from be_logbook.workflow.models import StageDependency


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = [
            "id",
            "code",
            "name",
            "description",
            "display_order",
            "required",
            "is_active",
            "guide_approval_required",
            "reviewer_approval_required",
            "document_required",
            "marks_required",
            "created_at",
            "updated_at",
        ]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = [
            "id",
            "stage",
            "section_type",
            "name",
            "description",
            "display_order",
            "required",
            "is_active",
        ]


class StageDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = StageDependency
        fields = ["id", "stage", "depends_on"]
