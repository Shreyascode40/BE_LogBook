from __future__ import annotations

from rest_framework import serializers

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import GuideAssignment
from be_logbook.groups.models import ProjectGroup
from be_logbook.users.models import User


class ProjectGroupSerializer(serializers.ModelSerializer):
    active_guide_id = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectGroup
        fields = [
            "id",
            "group_number",
            "academic_year",
            "department",
            "status",
            "current_stage",
            "active_guide_id",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "current_stage",
            "active_guide_id",
            "member_count",
        ]

    def get_active_guide_id(self, obj):
        guide = obj.active_guide
        return guide.id if guide else None

    def get_member_count(self, obj):
        return obj.memberships.filter(status="ACTIVE").count()


class GroupCreateSerializer(serializers.Serializer):
    group_number = serializers.CharField()
    academic_year_id = serializers.IntegerField()
    department_id = serializers.IntegerField()


class GroupMembershipSerializer(serializers.ModelSerializer):
    student_email = serializers.CharField(source="student.email", read_only=True)
    student_name = serializers.CharField(source="student.name", read_only=True)

    class Meta:
        model = GroupMembership
        fields = [
            "id",
            "group",
            "student",
            "student_email",
            "student_name",
            "status",
            "designation",
            "join_date",
            "leave_date",
        ]


class GuideAssignmentSerializer(serializers.ModelSerializer):
    faculty_email = serializers.CharField(source="faculty.email", read_only=True)

    class Meta:
        model = GuideAssignment
        fields = [
            "id",
            "group",
            "faculty",
            "faculty_email",
            "assigned_by",
            "assigned_at",
            "is_active",
            "end_date",
            "reason",
        ]


class AddMemberSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    designation = serializers.CharField(required=False, allow_blank=True, default="")


class AssignGuideSerializer(serializers.Serializer):
    faculty_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AssignReviewerSerializer(serializers.Serializer):
    reviewer_id = serializers.IntegerField()
    stage_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
