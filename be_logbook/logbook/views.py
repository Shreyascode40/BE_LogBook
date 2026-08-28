from __future__ import annotations

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from be_logbook.logbook.models import GeneratedLogBook
from be_logbook.logbook.services import LogBookPDFService
from be_logbook.projects.models import Project
from be_logbook.utils.access import can_access_group
from be_logbook.utils.exceptions import BusinessRuleViolation


class LogBookGenerateView(APIView):
    """POST /api/v1/projects/<project_id>/logbook/generate/"""

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
            gen = LogBookPDFService.generate(project, request.user, request=request)
        except BusinessRuleViolation as e:
            detail = e.detail.get("logbook", []) if hasattr(e, "detail") else []
            missing = [m for m in detail if m != "Final log book cannot be generated."]
            return Response(
                {
                    "success": False,
                    "message": "Final log book cannot be generated.",
                    "missing_items": missing,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        file_url = request.build_absolute_uri(
            reverse("logbook-api:download", args=[gen.id])
        )
        return Response(
            {
                "success": True,
                "message": "Final log book generated successfully.",
                "file_url": file_url,
                "page_count": gen.metadata.get("page_count", 40),
                "version": gen.version,
            }
        )


class LogBookRetrieveView(APIView):
    """GET /api/v1/projects/<project_id>/logbook/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        if not can_access_group(request.user, project.group):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        gens = GeneratedLogBook.objects.filter(project=project).order_by("-version")
        latest = gens.first()
        if latest is None:
            return Response(
                {
                    "success": True,
                    "exists": False,
                    "message": "No log book has been generated yet.",
                    "logbooks": [],
                }
            )
        file_url = request.build_absolute_uri(
            reverse("logbook-api:download", args=[latest.id])
        )
        return Response(
            {
                "success": True,
                "exists": True,
                "latest": {
                    "id": latest.id,
                    "version": latest.version,
                    "status": latest.status,
                    "template_version": latest.template_version,
                    "generated_at": latest.generated_at,
                    "generated_by": latest.generated_by.email,
                    "file_url": file_url,
                    "page_count": latest.metadata.get("page_count", 40),
                },
                "logbooks": [
                    {
                        "id": g.id,
                        "version": g.version,
                        "status": g.status,
                        "generated_at": g.generated_at,
                        "file_url": request.build_absolute_uri(
                            reverse("logbook-api:download", args=[g.id])
                        ),
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
                filename=f"Project_Log_Book_{gen.project.group.group_number}.pdf",
                content_type="application/pdf",
            )
        except FileNotFoundError:
            return Response(
                {"success": False, "message": "File not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
