from __future__ import annotations

from rest_framework import serializers

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.users.models import User


class StudentCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    roll_number = serializers.CharField()
    department_id = serializers.IntegerField()
    academic_year_id = serializers.IntegerField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, default="")


class FacultyCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    employee_id = serializers.CharField()
    department_id = serializers.IntegerField()
    designation = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")


class UserSummarySerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)
    student_profile = serializers.SerializerMethodField()
    faculty_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "is_active",
            "student_profile",
            "faculty_profile",
        ]

    def get_student_profile(self, obj):
        sp = getattr(obj, "student_profile", None)
        if not sp:
            return None
        return {
            "roll_number": sp.roll_number,
            "department_id": sp.department_id,
            "academic_year_id": sp.academic_year_id,
        }

    def get_faculty_profile(self, obj):
        fp = getattr(obj, "faculty_profile", None)
        if not fp:
            return None
        return {
            "employee_id": fp.employee_id,
            "department_id": fp.department_id,
            "designation": fp.designation,
        }
