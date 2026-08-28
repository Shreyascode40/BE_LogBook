from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings


@dataclass
class MemberData:
    name: str = ""
    roll_number: str = ""
    te_result: str = ""
    exam_seat_number: str = ""
    mobile: str = ""
    email: str = ""
    contribution: str = ""
    photo_path: str | None = None


@dataclass
class CompetitionData:
    name: str = ""
    date: str = ""
    college: str = ""
    level: str = ""
    participation_type: str = ""
    award: str = ""


@dataclass
class PublicationData:
    title: str = ""
    conference: str = ""
    issn: str = ""
    volume: str = ""
    page_no: str = ""


@dataclass
class LogBookData:
    # Identifiers
    department_name: str = ""
    academic_year: str = ""
    group_number: str = ""
    project_title: str = ""
    area: str = ""
    guide_name: str = ""

    # Topic finalization
    topic_1: str = ""
    topic_1_approved: bool | None = None
    topic_2: str = ""
    reviewer_1_name: str = ""
    reviewer_2_name: str = ""
    coordinator_name: str = ""

    # Members
    members: list[MemberData] = field(default_factory=list)

    # Schedule: item label -> date string
    schedule_dates: dict[str, str] = field(default_factory=dict)

    # Final evaluation committee
    evaluator_1_name: str = ""
    evaluator_2_name: str = ""

    # Competitions / publications
    competitions: list[CompetitionData] = field(default_factory=list)
    publications: list[PublicationData] = field(default_factory=list)

    # Sponsored
    is_sponsored: bool = False
    sponsored_company: str = ""

    # Raw handles (not rendered directly)
    project: Any = None
    group: Any = None


class LogBookDataAssembler:
    """Single source of truth: assembles approved project data for the PDF.

    Only real, stored values are collected. Anything missing is left as an
    empty string / None so the renderer preserves the blank field.
    """

    # Map the schedule row labels used in the template to Stage codes.
    SCHEDULE_STAGE_MAP = {
        "Group Submission": "GROUP_SUBMISSION",
        "Guide Allocation List": "GUIDE_ALLOCATION",
        "Topic Finalization Review": "TOPIC_FINALIZATION",
        "Synopsis/Abstract submission": "SYNOPSIS",
        "Review-1": "REVIEW_1",
        "Review-2": "REVIEW_2",
        "Review-3": "REVIEW_3",
        "Final Submission of Project report & Final Review": "FINAL_SUBMISSION",
        "Final Project Term - II Examination": "TERM_II_EXAM",
        "Final Term 1 Exam As per university schedule": "TERM_I_EXAM",
    }

    def __init__(self, project):
        self.project = project
        self.group = project.group

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def assemble(self) -> LogBookData:
        data = LogBookData(project=self.project, group=self.group)
        self._assemble_identifiers(data)
        self._assemble_members(data)
        self._assemble_topic(data)
        self._assemble_schedule(data)
        self._assemble_evaluators(data)
        self._assemble_competitions(data)
        self._assemble_publications(data)
        self._assemble_sponsorship(data)
        return data

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _assemble_identifiers(self, data: LogBookData) -> None:
        group = self.group
        data.department_name = group.department.name if group.department_id else ""
        data.academic_year = group.academic_year.name if group.academic_year_id else ""
        data.group_number = group.group_number or ""
        data.project_title = self.project.title or ""
        data.area = self.project.area or ""
        guide = self.project.guide or group.active_guide
        data.guide_name = guide.name if guide else ""

    def _assemble_members(self, data: LogBookData) -> None:
        from be_logbook.documents.models import Document

        # Map a membership's student to a PHOTO document if a profile photo
        # is not set directly.
        for membership in self.group.memberships.filter(status="ACTIVE").order_by(
            "join_date"
        ):
            student = membership.student
            sp = getattr(student, "student_profile", None)
            member = MemberData(
                name=student.name or "",
                contribution=membership.designation or "",
                mobile=sp.phone if sp else "",
                email=student.email or "",
            )
            if sp:
                member.roll_number = sp.roll_number or ""
                member.te_result = sp.te_result or ""
                member.exam_seat_number = sp.exam_seat_number or ""
                if sp.photo:
                    member.photo_path = self._media_path(sp.photo.name)
            if not member.photo_path:
                photo_doc = Document.objects.filter(
                    group=self.group,
                    document_type="PHOTO",
                    owner=student,
                    status="ACTIVE",
                ).first()
                if photo_doc:
                    member.photo_path = self._media_path(photo_doc.file.name)
            data.members.append(member)

    def _assemble_topic(self, data: LogBookData) -> None:
        tf = getattr(self.project, "topic_finalization", None)
        if tf:
            data.topic_1 = tf.finalized_topic or ""
            data.topic_1_approved = bool(tf.approved_by_id)
            data.topic_2 = ""  # template rule: only fill if topic 1 rejected
        # Reviewers for topic finalization (first two distinct reviewers)
        from be_logbook.reviews.models import ReviewAssignment

        reviewers = (
            ReviewAssignment.objects.filter(group=self.group, is_active=True)
            .select_related("reviewer")
            .order_by("assigned_at")
            .values_list("reviewer__name", flat=True)
            .distinct()[:2]
        )
        reviewers = [r for r in reviewers if r]
        if len(reviewers) > 0:
            data.reviewer_1_name = reviewers[0]
        if len(reviewers) > 1:
            data.reviewer_2_name = reviewers[1]

    def _assemble_schedule(self, data: LogBookData) -> None:
        from be_logbook.workflow.models import Stage, StageDeadline

        ay = self.group.academic_year
        for label, code in self.SCHEDULE_STAGE_MAP.items():
            stage = Stage.objects.filter(code=code).first()
            if not stage or not ay:
                continue
            deadline = StageDeadline.objects.filter(
                stage=stage, academic_year=ay
            ).first()
            if deadline and deadline.due_date:
                data.schedule_dates[label] = deadline.due_date.strftime("%d/%m/%Y")

    def _assemble_evaluators(self, data: LogBookData) -> None:
        from be_logbook.reviews.models import ReviewAssignment

        reviewers = (
            ReviewAssignment.objects.filter(group=self.group, is_active=True)
            .select_related("reviewer")
            .order_by("assigned_at")
            .values_list("reviewer__name", flat=True)
            .distinct()[:2]
        )
        reviewers = [r for r in reviewers if r]
        if len(reviewers) > 0:
            data.evaluator_1_name = reviewers[0]
        if len(reviewers) > 1:
            data.evaluator_2_name = reviewers[1]

    def _assemble_competitions(self, data: LogBookData) -> None:
        for comp in self.project.competitions.all():
            data.competitions.append(
                CompetitionData(
                    name=comp.name or "",
                    date=comp.date.strftime("%d/%m/%Y") if comp.date else "",
                    award=comp.prize or "",
                )
            )

    def _assemble_publications(self, data: LogBookData) -> None:
        for pub in self.project.publications.all():
            data.publications.append(
                PublicationData(
                    title=pub.title or "",
                    conference=pub.venue or "",
                )
            )

    def _assemble_sponsorship(self, data: LogBookData) -> None:
        from be_logbook.documents.models import Document

        sponsored = Document.objects.filter(
            group=self.group, document_type="SPONSORSHIP", status="ACTIVE"
        ).exists()
        data.is_sponsored = sponsored

    @staticmethod
    def _media_path(name: str) -> str | None:
        if not name:
            return None
        base = getattr(settings, "MEDIA_ROOT", None)
        if not base:
            return None
        path = os.path.join(base, name)
        return path if os.path.exists(path) else None
