from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion
from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.reviews.models import ReviewMark
from be_logbook.reviews.serializers import CorrectionSerializer
from be_logbook.reviews.serializers import MarkEntrySerializer
from be_logbook.reviews.serializers import ReviewAssignmentSerializer
from be_logbook.reviews.serializers import ReviewCreateSerializer
from be_logbook.reviews.serializers import ReviewSerializer
from be_logbook.reviews.services import ReviewService
from be_logbook.utils.access import can_access_review
from be_logbook.utils.exceptions import BusinessRuleViolation
from be_logbook.utils.permissions import IsHOD


class ReviewAssignmentViewSet(ModelViewSet):
    queryset = ReviewAssignment.objects.all().select_related(
        "group", "reviewer", "stage", "assigned_by"
    )
    serializer_class = ReviewAssignmentSerializer
    permission_classes = [IsHOD]
    filterset_fields = ["group", "stage", "reviewer", "is_active"]


class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all().select_related(
        "group", "reviewer", "stage", "rubric", "assignment"
    )
    serializer_class = ReviewSerializer
    filterset_fields = ["group", "stage", "reviewer", "status"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "HOD":
            return qs
        if user.role == "FACULTY":
            # Assigned reviewer sees own reviews; guides see group reviews.
            from be_logbook.groups.models import GuideAssignment

            gids = set(
                GuideAssignment.objects.filter(
                    faculty=user, is_active=True
                ).values_list("group_id", flat=True)
            )
            return qs.filter(reviewer=user) | qs.filter(group_id__in=gids)
        if user.role == "STUDENT":
            from be_logbook.groups.models import GroupMembership

            mids = GroupMembership.objects.filter(
                student=user, status="ACTIVE"
            ).values_list("group_id", flat=True)
            return qs.filter(group_id__in=mids)
        return qs.none()

    def create(self, request):
        # Reviewer (or HOD) creates a review for an assignment.
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assignment = get_object_or_404(ReviewAssignment, id=data["assignment_id"])
        rubric = get_object_or_404(Rubric, id=data["rubric_id"])
        if request.user.role not in ("HOD", "FACULTY"):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.role == "FACULTY" and assignment.reviewer_id != request.user.id:
            return Response(
                {"success": False, "message": "Not your assignment."},
                status=status.HTTP_403_FORBIDDEN,
            )
        review = Review.objects.create(
            assignment=assignment,
            group=assignment.group,
            reviewer=request.user,
            stage=assignment.stage,
            rubric=rubric,
            review_type=data["review_type"],
            date=data["date"],
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        review = self.get_object()
        if not can_access_review(request.user, review):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def enter_mark(self, request, pk=None):
        review = self.get_object()
        serializer = MarkEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        criterion = get_object_or_404(
            RubricCriterion,
            id=serializer.validated_data["criterion_id"],
            rubric=review.rubric,
        )
        try:
            ReviewService.enter_mark(
                review,
                criterion,
                serializer.validated_data["obtained"],
                serializer.validated_data["remarks"],
                request.user,
                request=request,
            )
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Invalid mark.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(ReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        review = self.get_object()
        try:
            ReviewService.submit(review, request.user, request=request)
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Cannot submit.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(ReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        review = self.get_object()
        try:
            ReviewService.finalize(review, request.user, request=request)
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Cannot finalize.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(ReviewSerializer(review).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHOD])
    def request_correction(self, request, pk=None):
        review = self.get_object()
        try:
            ReviewService.request_correction(
                review, request.user, request.data.get("reason", ""), request=request
            )
        except BusinessRuleViolation as e:
            return Response(
                {
                    "success": False,
                    "message": "Cannot request correction.",
                    "errors": e.detail,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(ReviewSerializer(review).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHOD])
    def correct_mark(self, request, pk=None):
        review = self.get_object()
        serializer = CorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        criterion = get_object_or_404(
            RubricCriterion,
            id=serializer.validated_data["criterion_id"],
            rubric=review.rubric,
        )
        try:
            ReviewService.correct_mark(
                review,
                criterion,
                serializer.validated_data["new_obtained"],
                request.user,
                serializer.validated_data["reason"],
                request=request,
            )
        except BusinessRuleViolation as e:
            return Response(
                {
                    "success": False,
                    "message": "Cannot correct mark.",
                    "errors": e.detail,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(ReviewSerializer(review).data)

    @action(detail=True, methods=["get"])
    def marks(self, request, pk=None):
        review = self.get_object()
        if not can_access_review(request.user, review):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            ReviewMark.objects.filter(review=review).values(
                "id", "criterion", "max_marks", "obtained_marks", "remarks"
            )
        )
