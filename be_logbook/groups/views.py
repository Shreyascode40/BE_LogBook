from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import GuideAssignment
from be_logbook.groups.models import ProjectGroup
from be_logbook.groups.serializers import AddMemberSerializer
from be_logbook.groups.serializers import AssignGuideSerializer
from be_logbook.groups.serializers import AssignReviewerSerializer
from be_logbook.groups.serializers import GroupCreateSerializer
from be_logbook.groups.serializers import GroupMembershipSerializer
from be_logbook.groups.serializers import GuideAssignmentSerializer
from be_logbook.groups.serializers import ProjectGroupSerializer
from be_logbook.groups.services import GroupService
from be_logbook.utils.access import can_access_group
from be_logbook.utils.access import is_hod
from be_logbook.utils.permissions import IsHOD
from be_logbook.utils.permissions import IsHODOrFaculty


class ProjectGroupViewSet(ModelViewSet):
    queryset = (
        ProjectGroup.objects.all()
        .select_related("academic_year", "department", "current_stage")
        .prefetch_related("memberships")
    )
    serializer_class = ProjectGroupSerializer
    permission_classes = [IsHODOrFaculty]
    filterset_fields = ["academic_year", "department", "status"]
    search_fields = ["group_number"]
    ordering = ["academic_year", "group_number"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_hod(user):
            return qs
        if user.role == "FACULTY":
            from be_logbook.reviews.models import ReviewAssignment

            assigned_group_ids = GuideAssignment.objects.filter(
                faculty=user, is_active=True
            ).values_list("group_id", flat=True)
            reviewer_ids = ReviewAssignment.objects.filter(
                reviewer=user, is_active=True
            ).values_list("group_id", flat=True)
            ids = set(assigned_group_ids) | set(reviewer_ids)
            return qs.filter(id__in=ids)
        if user.role == "STUDENT":
            from be_logbook.groups.models import GroupMembership as GM

            member_ids = GM.objects.filter(student=user, status="ACTIVE").values_list(
                "group_id", flat=True
            )
            return qs.filter(id__in=member_ids)
        return qs.none()

    def perform_create(self, serializer):
        # Creation handled via the create_group action (HOD only).
        raise NotImplementedError("Use the create_group action.")

    @action(detail=False, methods=["post"], permission_classes=[IsHOD])
    def create_group(self, request):
        serializer = GroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ay = AcademicYear.objects.get(id=data["academic_year_id"])
        dept = Department.objects.get(id=data["department_id"])
        group = GroupService.create_group(
            group_number=data["group_number"],
            academic_year=ay,
            department=dept,
            created_by=request.user,
            request=request,
        )
        return Response(
            ProjectGroupSerializer(group).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHOD])
    def add_member(self, request, pk=None):
        group = self.get_object()
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = get_object_or_404(
            User.objects.filter(role="STUDENT"),
            id=serializer.validated_data["student_id"],
        )
        membership = GroupService.add_member(
            group=group,
            student=student,
            designation=serializer.validated_data["designation"],
            created_by=request.user,
            request=request,
        )
        return Response(
            GroupMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHOD])
    def remove_member(self, request, pk=None):
        group = self.get_object()
        student = get_object_or_404(User, id=request.data.get("student_id"))
        GroupService.remove_member(
            group=group, student=student, created_by=request.user, request=request
        )
        return Response({"success": True, "message": "Member removed."})

    @action(detail=True, methods=["post"], permission_classes=[IsHOD])
    def assign_guide(self, request, pk=None):
        group = self.get_object()
        serializer = AssignGuideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        faculty = get_object_or_404(
            User.objects.filter(role="FACULTY"),
            id=serializer.validated_data["faculty_id"],
        )
        assignment = GroupService.assign_guide(
            group=group,
            faculty=faculty,
            assigned_by=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(
            GuideAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHOD])
    def assign_reviewer(self, request, pk=None):
        group = self.get_object()
        serializer = AssignReviewerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer = get_object_or_404(
            User.objects.filter(role="FACULTY"),
            id=serializer.validated_data["reviewer_id"],
        )
        from be_logbook.workflow.models import Stage

        stage = get_object_or_404(Stage, id=serializer.validated_data["stage_id"])
        assignment = GroupService.assign_reviewer(
            group=group,
            reviewer=reviewer,
            stage=stage,
            assigned_by=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(
            {"id": assignment.id, "message": "Reviewer assigned."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def stage_states(self, request, pk=None):
        group = self.get_object()
        if not can_access_group(request.user, group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from be_logbook.workflow.services import WorkflowService

        return Response({"success": True, "data": WorkflowService.stage_states(group)})

    @action(detail=True, methods=["get"])
    def full_detail(self, request, pk=None):
        group = self.get_object()
        if not can_access_group(request.user, group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from be_logbook.reviews.models import ReviewAssignment
        from be_logbook.submissions.models import Submission
        from be_logbook.workflow.services import WorkflowService

        data = {
            "group": ProjectGroupSerializer(group).data,
            "members": GroupMembershipSerializer(
                group.memberships.filter(status="ACTIVE"), many=True
            ).data,
            "guide": GuideAssignmentSerializer(
                GuideAssignment.objects.filter(group=group, is_active=True), many=True
            ).data,
            "reviewers": ReviewAssignment.objects.filter(
                group=group, is_active=True
            ).values("id", "reviewer", "stage"),
            "stage_states": WorkflowService.stage_states(group),
            "submissions": Submission.objects.filter(group=group).values(
                "id", "stage", "section", "status", "version_number"
            ),
        }
        return Response({"success": True, "data": data})

    def retrieve(self, request, *args, **kwargs):
        group = self.get_object()
        if not can_access_group(request.user, group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)
