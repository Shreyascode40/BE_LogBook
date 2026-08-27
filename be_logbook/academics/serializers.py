from __future__ import annotations

from rest_framework import serializers

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.academics.models import Term


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "code", "name", "is_active", "created_at", "updated_at"]


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = [
            "id",
            "name",
            "start_date",
            "end_date",
            "is_active",
            "is_archived",
            "created_at",
            "updated_at",
        ]


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = [
            "id",
            "academic_year",
            "name",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
        ]
