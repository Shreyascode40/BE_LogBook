from __future__ import annotations

from rest_framework import serializers

from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion


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


class RubricSerializer(serializers.ModelSerializer):
    criteria = RubricCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = Rubric
        fields = ["id", "name", "academic_year", "description", "is_active", "criteria"]


class RubricCriterionCreateSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    max_marks = serializers.DecimalField(max_digits=8, decimal_places=2)
    weight = serializers.DecimalField(max_digits=6, decimal_places=2, default=1)
    co_code = serializers.CharField(required=False, allow_blank=True, default="")
    po_code = serializers.CharField(required=False, allow_blank=True, default="")
    is_required = serializers.BooleanField(default=True)
