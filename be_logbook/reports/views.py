from __future__ import annotations

from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from be_logbook.reports.services import ReportService
from be_logbook.utils.permissions import IsHOD


class ReportViewSet(ViewSet):
    permission_classes = [IsHOD]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        ay = request.query_params.get("academic_year")
        return Response(ReportService.overview(ay))

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        ay = request.query_params.get("academic_year")
        groups = ReportService.overdue_groups(ay)
        return Response(
            {
                "count": groups.count(),
                "groups": list(
                    groups.values("id", "group_number", "status", "current_stage")
                ),
            }
        )

    @action(detail=False, methods=["get"])
    def faculty_workload(self, request):
        return Response(ReportService.faculty_workload())

    @action(detail=False, methods=["get"])
    def reviewer_workload(self, request):
        return Response(ReportService.reviewer_workload())

    @action(detail=False, methods=["get"])
    def group_progress(self, request):
        ay = request.query_params.get("academic_year")
        return Response(ReportService.group_progress(ay))

    @action(detail=False, methods=["get"])
    def export(self, request):
        fmt = request.query_params.get("fmt", "csv")
        ay = request.query_params.get("academic_year")
        progress = ReportService.group_progress(ay)
        if fmt == "csv":
            import csv
            import io

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["group_id", "group_number", "status", "progress_percent"])
            for row in progress:
                writer.writerow(
                    [
                        row["group_id"],
                        row["group_number"],
                        row["status"],
                        row["progress_percent"],
                    ]
                )
            return HttpResponse(buf.getvalue(), content_type="text/csv")
        return Response(
            {"success": False, "message": "Unsupported format."}, status=400
        )
