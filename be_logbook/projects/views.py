from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.projects.models import CompetitionDetail
from be_logbook.projects.models import FinalSubmissionInfo
from be_logbook.projects.models import Project
from be_logbook.projects.models import ProjectSchedule
from be_logbook.projects.models import PublicationDetail
from be_logbook.projects.models import TermRecord
from be_logbook.projects.models import TopicFinalization
from be_logbook.projects.serializers import CompetitionDetailSerializer
from be_logbook.projects.serializers import FinalSubmissionInfoSerializer
from be_logbook.projects.serializers import ProjectScheduleSerializer
from be_logbook.projects.serializers import ProjectSerializer
from be_logbook.projects.serializers import PublicationDetailSerializer
from be_logbook.projects.serializers import TermRecordSerializer
from be_logbook.projects.serializers import TopicFinalizationSerializer
from be_logbook.utils.access import can_access_group
from be_logbook.utils.permissions import IsHODOrFaculty


def _project_accessible(user, project):
    return can_access_group(user, project.group)


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all().select_related("group", "guide")
    serializer_class = ProjectSerializer
    permission_classes = [IsHODOrFaculty]
    filterset_fields = ["group", "area"]
    search_fields = ["title", "area"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "HOD":
            return qs
        if user.role == "FACULTY":
            from be_logbook.groups.models import GuideAssignment
            from be_logbook.reviews.models import ReviewAssignment

            gids = set(
                GuideAssignment.objects.filter(
                    faculty=user, is_active=True
                ).values_list("group_id", flat=True)
            )
            rids = set(
                ReviewAssignment.objects.filter(
                    reviewer=user, is_active=True
                ).values_list("group_id", flat=True)
            )
            return qs.filter(group_id__in=gids | rids)
        if user.role == "STUDENT":
            from be_logbook.groups.models import GroupMembership

            mids = GroupMembership.objects.filter(
                student=user, status="ACTIVE"
            ).values_list("group_id", flat=True)
            return qs.filter(group_id__in=mids)
        return qs.none()

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if not _project_accessible(request.user, obj):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        if not _project_accessible(request.user, obj):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)


class _ProjectChildViewSet(ModelViewSet):
    """Base for project-child models with project-based access control."""

    permission_classes = [IsHODOrFaculty]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "HOD":
            return qs
        from be_logbook.groups.models import GuideAssignment
        from be_logbook.reviews.models import ReviewAssignment
        from be_logbook.groups.models import GroupMembership

        gids = set(
            GuideAssignment.objects.filter(faculty=user, is_active=True).values_list(
                "group_id", flat=True
            )
        )
        rids = set(
            ReviewAssignment.objects.filter(reviewer=user, is_active=True).values_list(
                "group_id", flat=True
            )
        )
        mids = set(
            GroupMembership.objects.filter(student=user, status="ACTIVE").values_list(
                "group_id", flat=True
            )
        )
        allowed = gids | rids | mids
        return qs.filter(project__group_id__in=allowed)


class ProjectScheduleViewSet(_ProjectChildViewSet):
    queryset = ProjectSchedule.objects.all().select_related("project__group")
    serializer_class = ProjectScheduleSerializer


class TopicFinalizationViewSet(_ProjectChildViewSet):
    queryset = TopicFinalization.objects.all().select_related("project__group")
    serializer_class = TopicFinalizationSerializer


class FinalSubmissionInfoViewSet(_ProjectChildViewSet):
    queryset = FinalSubmissionInfo.objects.all().select_related("project__group")
    serializer_class = FinalSubmissionInfoSerializer


class CompetitionDetailViewSet(_ProjectChildViewSet):
    queryset = CompetitionDetail.objects.all().select_related("project__group")
    serializer_class = CompetitionDetailSerializer


class PublicationDetailViewSet(_ProjectChildViewSet):
    queryset = PublicationDetail.objects.all().select_related("project__group")
    serializer_class = PublicationDetailSerializer


class TermRecordViewSet(_ProjectChildViewSet):
    queryset = TermRecord.objects.all().select_related("project__group")
    serializer_class = TermRecordSerializer
