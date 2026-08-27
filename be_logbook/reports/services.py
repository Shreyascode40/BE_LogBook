from __future__ import annotations

from collections import Counter
from datetime import date

from django.db.models import Count
from django.db.models import Q

from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import GuideAssignment
from be_logbook.groups.models import ProjectGroup
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.submissions.models import Submission
from be_logbook.workflow.models import Stage
from be_logbook.workflow.models import StageDeadline


class ReportService:
    """Aggregated reporting for HOD dashboards."""

    @staticmethod
    def overview(academic_year_id=None):
        qs = ProjectGroup.objects.all()
        if academic_year_id:
            qs = qs.filter(academic_year_id=academic_year_id)
        total = qs.count()
        by_status = dict(
            qs.values_list("status")
            .annotate(cnt=Count("id"))
            .values_list("status", "cnt")
        )
        completed = by_status.get("COMPLETED", 0)
        in_progress = by_status.get("IN_PROGRESS", 0)
        under_review = by_status.get("UNDER_REVIEW", 0)
        changes_required = by_status.get("CHANGES_REQUIRED", 0)
        overdue = ReportService.overdue_groups(academic_year_id).count()
        return {
            "total_groups": total,
            "completed_groups": completed,
            "in_progress_groups": in_progress,
            "under_review_groups": under_review,
            "changes_required_groups": changes_required,
            "overdue_groups": overdue,
            "by_status": by_status,
        }

    @staticmethod
    def overdue_groups(academic_year_id=None):
        today = date.today()
        deadline_q = StageDeadline.objects.filter(
            submission_deadline__lt=today
        ).values_list("stage_id", flat=True)
        qs = ProjectGroup.objects.filter(
            current_stage_id__in=list(deadline_q),
            status__in=["IN_PROGRESS", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUIRED"],
        )
        if academic_year_id:
            qs = qs.filter(academic_year_id=academic_year_id)
        return qs

    @staticmethod
    def faculty_workload():
        rows = []
        for ga in GuideAssignment.objects.filter(is_active=True).select_related(
            "faculty", "group"
        ):
            pending = Submission.objects.filter(
                group=ga.group, status__in=["SUBMITTED", "RESUBMITTED", "UNDER_REVIEW"]
            ).count()
            rows.append(
                {
                    "faculty_id": ga.faculty_id,
                    "faculty_email": ga.faculty.email,
                    "group_id": ga.group_id,
                    "group_number": ga.group.group_number,
                    "pending_submissions": pending,
                }
            )
        return rows

    @staticmethod
    def reviewer_workload():
        rows = []
        for ra in ReviewAssignment.objects.filter(is_active=True).select_related(
            "reviewer", "group", "stage"
        ):
            pending_reviews = ra.reviews.filter(
                status__in=["DRAFT", "SUBMITTED"]
            ).count()
            rows.append(
                {
                    "reviewer_id": ra.reviewer_id,
                    "reviewer_email": ra.reviewer.email,
                    "group_id": ra.group_id,
                    "stage_id": ra.stage_id,
                    "stage_name": ra.stage.name,
                    "pending_reviews": pending_reviews,
                }
            )
        return rows

    @staticmethod
    def group_progress(academic_year_id=None):
        qs = ProjectGroup.objects.all().select_related("academic_year", "department")
        if academic_year_id:
            qs = qs.filter(academic_year_id=academic_year_id)
        out = []
        for group in qs:
            total_required = Stage.objects.filter(is_active=True, required=True).count()
            satisfied = sum(
                1
                for s in Stage.objects.filter(is_active=True, required=True)
                if Submission.objects.filter(
                    group=group, stage=s, status__in=["APPROVED", "LOCKED"]
                ).exists()
            )
            percent = int((satisfied / total_required) * 100) if total_required else 0
            out.append(
                {
                    "group_id": group.id,
                    "group_number": group.group_number,
                    "status": group.status,
                    "progress_percent": percent,
                }
            )
        return out
