from __future__ import annotations

from typing import Tuple

from be_logbook.projects.models import Project


class LogBookValidationService:
    """Eligibility gate: a final log book is only generated from approved data.

    Every check reads the database (the source of truth). If any mandatory
    item is missing the PDF is NOT generated with fabricated content.
    """

    REQUIRED_DOCUMENT_TYPES = ["REPORT"]

    @classmethod
    def validate(cls, project: Project) -> Tuple[bool, list[str]]:
        missing: list[str] = []

        group = project.group
        if not group:
            return False, ["Project is not linked to a group."]

        # Student information completeness
        cls._check_students(group, missing)

        # Required project information
        if not project.title:
            missing.append("Project title is missing.")
        if not (project.guide_id or group.active_guide_id):
            missing.append("Project guide is not assigned.")

        # Required stages approved
        cls._check_stages(group, missing)

        # Required documents
        cls._check_documents(group, missing)

        # Reviews finalized
        cls._check_reviews(group, missing)

        # Final submission completed
        cls._check_final_submission(project, missing)

        return (len(missing) == 0, missing)

    @staticmethod
    def _check_students(group, missing: list[str]) -> None:
        from be_logbook.groups.models import GroupMembership

        members = GroupMembership.objects.filter(
            group=group, status="ACTIVE"
        ).select_related("student__student_profile")
        if not members.exists():
            missing.append("Group has no active student members.")
            return
        for m in members:
            sp = getattr(m.student, "student_profile", None)
            if not m.student.name:
                missing.append(f"Student name missing for a group member.")
            if not sp or not sp.roll_number:
                missing.append(f"Roll number missing for {m.student.email}.")

    @staticmethod
    def _check_stages(group, missing: list[str]) -> None:
        from be_logbook.submissions.models import Submission
        from be_logbook.workflow.models import Stage

        for stage in Stage.objects.filter(is_active=True, required=True):
            approved = Submission.objects.filter(
                group=group, stage=stage, status__in=["APPROVED", "LOCKED"]
            ).exists()
            if not approved:
                missing.append(f"Stage not approved: {stage.name}")

    @staticmethod
    def _check_documents(group, missing: list[str]) -> None:
        from be_logbook.documents.models import Document

        for dtype in LogBookValidationService.REQUIRED_DOCUMENT_TYPES:
            if not Document.objects.filter(
                group=group, document_type=dtype, status="ACTIVE"
            ).exists():
                missing.append(f"Missing required document: {dtype}")

    @staticmethod
    def _check_reviews(group, missing: list[str]) -> None:
        from be_logbook.reviews.models import Review

        pending = Review.objects.filter(
            group=group,
            status__in=["DRAFT", "SUBMITTED", "CORRECTION_REQUESTED", "CORRECTED"],
        ).exists()
        if pending:
            missing.append("Some reviews are not finalized.")

    @staticmethod
    def _check_final_submission(project, missing: list[str]) -> None:
        fs = getattr(project, "final_submission", None)
        if not fs or not fs.submitted:
            missing.append("Final project submission is not completed.")
