from __future__ import annotations

from rest_framework import serializers

from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion
from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.reviews.models import ReviewMark


class ReviewAssignmentSerializer(serializers.ModelSerializer):
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True)

    class Meta:
        model = ReviewAssignment
        fields = [
            "id",
            "group",
            "reviewer",
            "reviewer_email",
            "stage",
            "stage_name",
            "assigned_by",
            "assigned_at",
            "is_active",
            "end_date",
            "reason",
        ]


class RubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rubric
        fields = ["id", "name", "academic_year", "description", "is_active"]


class RubricCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubricCriterion
        fields = [
            "id",
            "rubric",
            "code",
            "name",
            "description",
            "max_marks",
            "weight",
            "co_code",
            "po_code",
            "order",
            "is_required",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "assignment",
            "group",
            "reviewer",
            "reviewer_email",
            "stage",
            "stage_name",
            "rubric",
            "review_type",
            "date",
            "status",
            "total_max",
            "total_obtained",
            "remarks",
            "finalized_at",
            "finalized_by",
            "created_at",
            "updated_at",
        ]


class ReviewCreateSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField()
    rubric_id = serializers.IntegerField()
    review_type = serializers.CharField(default="INTERNAL")
    date = serializers.DateField()


class MarkEntrySerializer(serializers.Serializer):
    criterion_id = serializers.IntegerField()
    obtained = serializers.DecimalField(max_digits=8, decimal_places=2)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CorrectionSerializer(serializers.Serializer):
    criterion_id = serializers.IntegerField()
    new_obtained = serializers.DecimalField(max_digits=8, decimal_places=2)
    reason = serializers.CharField()
