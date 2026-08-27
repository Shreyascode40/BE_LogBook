from __future__ import annotations

from rest_framework import serializers

from be_logbook.projects.models import CompetitionDetail
from be_logbook.projects.models import FinalSubmissionInfo
from be_logbook.projects.models import Project
from be_logbook.projects.models import ProjectSchedule
from be_logbook.projects.models import PublicationDetail
from be_logbook.projects.models import TermRecord
from be_logbook.projects.models import TopicFinalization


class ProjectSerializer(serializers.ModelSerializer):
    guide_id = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "group",
            "title",
            "area",
            "description",
            "guide_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["guide_id"]

    def get_guide_id(self, obj):
        return obj.guide_id


class ProjectScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSchedule
        fields = [
            "id",
            "project",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
            "milestones",
        ]


class TopicFinalizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicFinalization
        fields = [
            "id",
            "project",
            "finalized_topic",
            "finalized_date",
            "approved_by",
            "notes",
        ]


class FinalSubmissionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalSubmissionInfo
        fields = [
            "id",
            "project",
            "submitted",
            "submitted_date",
            "certificate",
            "notes",
        ]


class CompetitionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionDetail
        fields = [
            "id",
            "project",
            "name",
            "date",
            "prize",
            "certificate",
            "description",
        ]


class PublicationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicationDetail
        fields = [
            "id",
            "project",
            "title",
            "venue",
            "date",
            "link",
            "certificate",
            "description",
        ]


class TermRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermRecord
        fields = ["id", "project", "term", "start_date", "end_date", "description"]
