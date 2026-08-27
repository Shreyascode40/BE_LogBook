from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = get_user_model().USERNAME_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if not user.is_active:
            msg = "This account is inactive."
            raise serializers.ValidationError(msg)
        data["user"] = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        }
        return data


class UserDetailSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)
    student_profile = serializers.SerializerMethodField()
    faculty_profile = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "email", "name", "role", "student_profile", "faculty_profile"]

    def get_student_profile(self, obj):
        sp = getattr(obj, "student_profile", None)
        if not sp:
            return None
        return {
            "roll_number": sp.roll_number,
            "phone": sp.phone,
            "department": sp.department_id,
            "academic_year": sp.academic_year_id,
        }

    def get_faculty_profile(self, obj):
        fp = getattr(obj, "faculty_profile", None)
        if not fp:
            return None
        return {
            "employee_id": fp.employee_id,
            "designation": fp.designation,
            "department": fp.department_id,
            "phone": fp.phone,
        }
