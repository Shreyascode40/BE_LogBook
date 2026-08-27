from __future__ import annotations

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.documents.models import Document
from be_logbook.documents.models import DocumentVersion
from be_logbook.documents.serializers import DocumentSerializer
from be_logbook.documents.serializers import DocumentUploadSerializer
from be_logbook.documents.serializers import DocumentVersionSerializer
from be_logbook.documents.services import DocumentService
from be_logbook.utils.access import can_access_document
from be_logbook.utils.exceptions import BusinessRuleViolation


class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all().select_related("group", "project", "uploaded_by")
    serializer_class = DocumentSerializer
    filterset_fields = ["group", "project", "document_type", "status"]
    ordering = ["-created_at"]

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
            return qs.filter(group_id__in=mids) | qs.filter(owner=user)
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

    def create(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        group = None
        project = None
        stage = None
        owner = None
        if data.get("group_id"):
            from be_logbook.groups.models import ProjectGroup

            group = get_object_or_404(ProjectGroup, id=data["group_id"])
        if data.get("project_id"):
            from be_logbook.projects.models import Project

            project = get_object_or_404(Project, id=data["project_id"])
        if data.get("stage_id"):
            from be_logbook.workflow.models import Stage

            stage = get_object_or_404(Stage, id=data["stage_id"])
        if data.get("owner_id"):
            from be_logbook.users.models import User

            owner = get_object_or_404(User, id=data["owner_id"])
        try:
            doc = DocumentService.upload(
                document_type=data["document_type"],
                file_obj=data["file"],
                user=request.user,
                group=group,
                project=project,
                stage=stage,
                owner=owner,
                request=request,
            )
        except BusinessRuleViolation as e:
            return Response(
                {"success": False, "message": "Upload rejected.", "errors": e.detail},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        if not can_access_document(request.user, document):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            return FileResponse(
                document.file.open("rb"),
                as_attachment=True,
                filename=document.original_filename or f"doc_{document.id}",
                content_type=document.mime_type or "application/octet-stream",
            )
        except FileNotFoundError:
            return Response(
                {"success": False, "message": "File not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        document = self.get_object()
        if not can_access_document(request.user, document):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            DocumentVersionSerializer(
                DocumentVersion.objects.filter(document=document), many=True
            ).data
        )
