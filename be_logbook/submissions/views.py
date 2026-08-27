from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.submissions.models import Approval
from be_logbook.submissions.models import ChangeRequest
from be_logbook.submissions.models import FacultyRemark
from be_logbook.submissions.models import Submission
from be_logbook.submissions.models import SubmissionVersion
from be_logbook.submissions.serializers import ApprovalSerializer
from be_logbook.submissions.serializers import ChangeRequestSerializer
from be_logbook.submissions.serializers import FacultyRemarkSerializer
from be_logbook.submissions.serializers import SubmissionActionSerializer
from be_logbook.submissions.serializers import SubmissionCreateSerializer
from be_logbook.submissions.serializers import SubmissionSerializer
from be_logbook.submissions.serializers import SubmissionVersionSerializer
from be_logbook.submissions.services import SubmissionService
from be_logbook.utils.access import can_access_submission
from be_logbook.utils.access import is_group_member
from be_logbook.utils.access import is_student
from be_logbook.utils.exceptions import BusinessRuleViolation
from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage

SUBMIT_ACTIONS = {
    "save_draft": ("save_draft", "data"),
    "submit": ("submit", None),
    "begin_review": ("begin_review", None),
    "request_changes": ("request_changes", "text"),
    "approve": ("approve", "remarks"),
    "lock": ("lock", None),
}


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all().select_related(
        "group", "stage", "section", "submitted_by"
    )
    serializer_class = SubmissionSerializer
    permission_classes = []  # per-action / object checks
    filterset_fields = ["group", "stage", "section", "status"]
    ordering = ["group", "stage", "section"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "HOD":
            return qs
        if user.role == "STUDENT":
            from be_logbook.groups.models import GroupMembership

            mids = GroupMembership.objects.filter(
                student=user, status="ACTIVE"
            ).values_list("group_id", flat=True)
            return qs.filter(group_id__in=mids)
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
        return qs.none()

    def _check_access(self, submission):
        if not can_access_submission(self.request.user, submission):
            return False
        return True

    def retrieve(self, request, *args, **kwargs):
        submission = self.get_object()
        if not self._check_access(submission):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

    def create(self, request):
        if not is_student(request.user):
            return Response(
                {"success": False, "message": "Only students create submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from be_logbook.groups.models import ProjectGroup

        group = get_object_or_404(ProjectGroup, id=data["group_id"])
        if not is_group_member(request.user, group):
            return Response(
                {"success": False, "message": "Not a member of this group."},
                status=status.HTTP_403_FORBIDDEN,
            )
        stage = get_object_or_404(Stage, id=data["stage_id"])
        section = get_object_or_404(Section, id=data["section_id"])
        from be_logbook.workflow.services import WorkflowService

        if not WorkflowService.is_stage_unlocked(group, stage):
            return Response(
                {"success": False, "message": "Stage is locked."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        submission, _ = Submission.objects.get_or_create(
            group=group,
            stage=stage,
            section=section,
            defaults={"submitted_by": request.user, "data": data.get("data", {})},
        )
        if submission.status not in ("DRAFT", "CHANGES_REQUIRED", "RESUBMITTED"):
            return Response(
                {"success": False, "message": "Submission already finalized."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        submission.data = data.get("data", submission.data)
        submission.save(update_fields=["data", "updated_at"])
        return Response(
            SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def save_draft(self, request, pk=None):
        submission = self.get_object()
        serializer = SubmissionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            SubmissionService.save_draft(
                submission,
                request.user,
                serializer.validated_data.get("data", {}),
                request=request,
            )
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Cannot save draft.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(SubmissionSerializer(submission).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        submission = self.get_object()
        try:
            submission, _ = SubmissionService.submit(
                submission, request.user, request=request
            )
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Cannot submit.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(SubmissionSerializer(submission).data)

    @action(detail=True, methods=["post"])
    def begin_review(self, request, pk=None):
        submission = self.get_object()
        try:
            SubmissionService.begin_review(submission, request.user, request=request)
        except BusinessRuleViolation as e:
            return Response(
                {
                    "success": False,
                    "message": "Cannot begin review.",
                    "errors": e.detail,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(SubmissionSerializer(submission).data)

    @action(detail=True, methods=["post"])
    def request_changes(self, request, pk=None):
        submission = self.get_object()
        serializer = SubmissionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            SubmissionService.request_changes(
                submission,
                request.user,
                serializer.validated_data.get("text", ""),
                request=request,
            )
        except BusinessRuleViolation as e:
            return Response(
                {
                    "success": False,
                    "message": "Cannot request changes.",
                    "errors": e.detail,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(SubmissionSerializer(submission).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        submission = self.get_object()
        serializer = SubmissionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            SubmissionService.approve(
                submission,
                request.user,
                serializer.validated_data.get("remarks", ""),
                request=request,
            )
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Cannot approve.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(SubmissionSerializer(submission).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        submission = self.get_object()
        try:
            SubmissionService.lock(submission, request.user, request=request)
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Cannot lock.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(SubmissionSerializer(submission).data)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        submission = self.get_object()
        if not self._check_access(submission):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        versions = SubmissionVersion.objects.filter(submission=submission)
        return Response(SubmissionVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"])
    def remarks(self, request, pk=None):
        submission = self.get_object()
        if not self._check_access(submission):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            FacultyRemarkSerializer(
                FacultyRemark.objects.filter(submission=submission), many=True
            ).data
        )

    @action(detail=True, methods=["get"])
    def approvals(self, request, pk=None):
        submission = self.get_object()
        if not self._check_access(submission):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            ApprovalSerializer(
                Approval.objects.filter(submission=submission), many=True
            ).data
        )

    @action(detail=True, methods=["get"])
    def change_requests(self, request, pk=None):
        submission = self.get_object()
        if not self._check_access(submission):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            ChangeRequestSerializer(
                ChangeRequest.objects.filter(submission=submission), many=True
            ).data
        )
