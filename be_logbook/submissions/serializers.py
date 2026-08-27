from __future__ import annotations

from rest_framework import serializers

from be_logbook.submissions.models import Approval
from be_logbook.submissions.models import ChangeRequest
from be_logbook.submissions.models import FacultyRemark
from be_logbook.submissions.models import Submission
from be_logbook.submissions.models import SubmissionVersion
from be_logbook.users.models import User
from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage


class SubmissionSerializer(serializers.ModelSerializer):
    submitted_by_email = serializers.CharField(
        source="submitted_by.email", read_only=True
    )
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "group",
            "project",
            "stage",
            "stage_name",
            "section",
            "section_name",
            "submitted_by",
            "submitted_by_email",
            "status",
            "version_number",
            "data",
            "current_approved_version",
            "submitted_at",
            "reviewed_at",
            "approved_at",
            "locked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "version_number",
            "submitted_at",
            "reviewed_at",
            "approved_at",
            "locked_at",
            "current_approved_version",
        ]


class SubmissionCreateSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    stage_id = serializers.IntegerField()
    section_id = serializers.IntegerField()
    data = serializers.JSONField(default=dict, required=False)


class SubmissionActionSerializer(serializers.Serializer):
    data = serializers.JSONField(default=dict, required=False)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    text = serializers.CharField(required=False, allow_blank=True, default="")


class SubmissionVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionVersion
        fields = [
            "id",
            "version_number",
            "status",
            "data",
            "submitted_by",
            "remarks",
            "created_at",
        ]


class FacultyRemarkSerializer(serializers.ModelSerializer):
    author_email = serializers.CharField(source="author.email", read_only=True)

    class Meta:
        model = FacultyRemark
        fields = [
            "id",
            "submission",
            "author",
            "author_email",
            "role",
            "text",
            "version",
            "created_at",
        ]


class ApprovalSerializer(serializers.ModelSerializer):
    approver_email = serializers.CharField(source="approver.email", read_only=True)

    class Meta:
        model = Approval
        fields = [
            "id",
            "submission",
            "approver",
            "approver_email",
            "role",
            "decision",
            "remarks",
            "version",
            "timestamp",
        ]


class ChangeRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.CharField(
        source="requested_by.email", read_only=True
    )

    class Meta:
        model = ChangeRequest
        fields = [
            "id",
            "submission",
            "requested_by",
            "requested_by_email",
            "text",
            "created_at",
            "resolved",
            "resolved_at",
            "resolution_remarks",
        ]
