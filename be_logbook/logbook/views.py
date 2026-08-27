from __future__ import annotations

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from be_logbook.logbook.models import GeneratedLogBook
from be_logbook.logbook.services import LogBookGenerationService
from be_logbook.projects.models import Project
from be_logbook.utils.access import can_access_group
from be_logbook.utils.exceptions import BusinessRuleViolation


class LogBookGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        if not can_access_group(request.user, project.group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if (
            request.user.role == "STUDENT"
            and not project.group.memberships.filter(
                student=request.user, status="ACTIVE"
            ).exists()
        ):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            gen = LogBookGenerationService.generate(
                project, request.user, request=request
            )
        except BusinessRuleViolation as e:
            return Response(
                {
                    "success": False,
                    "message": "Cannot generate logbook.",
                    "errors": e.detail,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(
            {
                "success": True,
                "id": gen.id,
                "version": gen.version,
                "status": gen.status,
            }
        )

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        if not can_access_group(request.user, project.group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        gens = GeneratedLogBook.objects.filter(project=project)
        return Response(
            {
                "count": gens.count(),
                "logbooks": [
                    {
                        "id": g.id,
                        "version": g.version,
                        "status": g.status,
                        "generated_at": g.generated_at,
                    }
                    for g in gens
                ],
            }
        )


class LogBookDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        gen = get_object_or_404(GeneratedLogBook, id=pk)
        if not can_access_group(request.user, gen.project.group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            return FileResponse(
                gen.file.open("rb"),
                as_attachment=True,
                filename=f"logbook_{gen.id}.pdf",
                content_type="application/pdf",
            )
        except FileNotFoundError:
            return Response(
                {"success": False, "message": "File not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
