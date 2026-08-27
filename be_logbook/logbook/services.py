from __future__ import annotations

import io
import uuid
from datetime import datetime

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from be_logbook.utils.exceptions import BusinessRuleViolation

from .models import GeneratedLogBook


class LogBookGenerationService:
    """Validates completion and generates the final logbook PDF.

    The backend is the source of truth: generation is refused unless every
    required stage has an approved submission, required documents exist, and
    all reviews are finalized.
    """

    REQUIRED_DOCUMENT_TYPES = ["REPORT"]

    @classmethod
    def validate(cls, project) -> tuple[bool, list[str]]:
        missing: list[str] = []
        group = project.group
        from be_logbook.workflow.models import Stage
        from be_logbook.submissions.models import Submission

        for stage in Stage.objects.filter(is_active=True, required=True):
            approved = Submission.objects.filter(
                group=group, stage=stage, status__in=["APPROVED", "LOCKED"]
            ).exists()
            if not approved:
                missing.append(f"Stage not approved: {stage.name}")
        from be_logbook.documents.models import Document

        for dtype in cls.REQUIRED_DOCUMENT_TYPES:
            if not Document.objects.filter(
                group=group, document_type=dtype, status="ACTIVE"
            ).exists():
                missing.append(f"Missing required document: {dtype}")
        from be_logbook.reviews.models import Review

        pending_reviews = Review.objects.filter(
            group=group, status__in=["DRAFT", "SUBMITTED", "CORRECTION_REQUESTED"]
        ).exists()
        if pending_reviews:
            missing.append("Some reviews are not finalized.")
        return (len(missing) == 0, missing)

    @classmethod
    @transaction.atomic
    def generate(cls, project, user, request=None) -> GeneratedLogBook:
        ok, missing = cls.validate(project)
        if not ok:
            raise BusinessRuleViolation(
                {"logbook": [f"Cannot generate logbook. Missing: {'; '.join(missing)}"]}
            )
        version = GeneratedLogBook.objects.filter(project=project).count() + 1
        pdf_bytes = cls._build_pdf(project)
        gen = GeneratedLogBook.objects.create(
            project=project,
            generated_by=user,
            version=version,
            status="READY",
            metadata={"generated_at": timezone.now().isoformat()},
        )
        filename = f"logbook_v{version}_{uuid.uuid4().hex[:8]}.pdf"
        gen.file.save(filename, File(io.BytesIO(pdf_bytes)), save=True)
        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=user,
            action="LOGBOOK_GENERATED",
            entity="GeneratedLogBook",
            object_id=gen.id,
            new_state=f"v{version}",
            request=request,
        )
        return gen

    @classmethod
    def _build_pdf(cls, project) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph
        from reportlab.platypus import SimpleDocTemplate
        from reportlab.platypus import Spacer
        from reportlab.platypus import Table

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"Log Book - {project.title}",
        )
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("BE Project Log Book", styles["Title"]))
        story.append(Spacer(1, 0.5 * cm))
        group = project.group
        guide = project.guide
        data = [
            ["Project Title", project.title],
            ["Area / Domain", project.area or "-"],
            ["Group", str(group)],
            ["Guide", guide.email if guide else "-"],
            ["Academic Year", str(group.academic_year)],
            ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ]
        story.append(Table(data, colWidths=[5 * cm, 11 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        # Members
        story.append(Paragraph("Group Members", styles["Heading2"]))
        member_rows = [["#", "Student", "Roll Number", "Email"]]
        for i, m in enumerate(group.memberships.filter(status="ACTIVE"), 1):
            sp = getattr(m.student, "student_profile", None)
            member_rows.append(
                [
                    str(i),
                    m.student.name,
                    sp.roll_number if sp else "-",
                    m.student.email,
                ]
            )
        story.append(Table(member_rows, colWidths=[1 * cm, 5 * cm, 4 * cm, 6 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        # Submissions summary
        story.append(Paragraph("Stage Submissions", styles["Heading2"]))
        from be_logbook.submissions.models import Submission
        from be_logbook.workflow.models import Stage

        sub_rows = [["Stage", "Section", "Status", "Version"]]
        for stage in Stage.objects.filter(is_active=True).order_by("display_order"):
            for sub in Submission.objects.filter(group=group, stage=stage):
                sub_rows.append(
                    [
                        stage.name,
                        sub.section.name,
                        sub.status,
                        str(sub.version_number),
                    ]
                )
        story.append(Table(sub_rows, colWidths=[5 * cm, 5 * cm, 4 * cm, 2 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        # Reviews / marks
        story.append(Paragraph("Review Marks", styles["Heading2"]))
        from be_logbook.reviews.models import Review

        rev_rows = [["Stage", "Reviewer", "Status", "Obtained / Max"]]
        for rev in Review.objects.filter(group=group):
            rev_rows.append(
                [
                    rev.stage.name,
                    rev.reviewer.email,
                    rev.status,
                    f"{rev.total_obtained} / {rev.total_max}",
                ]
            )
        story.append(Table(rev_rows, colWidths=[5 * cm, 5 * cm, 3 * cm, 3 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        # CO/PO attainment
        story.append(Paragraph("CO / PO Attainment", styles["Heading2"]))
        from be_logbook.co_po.services import COPOService

        attainment = COPOService.compute_for_group(group)
        co_rows = [["CO", "Attainment %"]] + [
            [k, f"{v:.2f}"] for k, v in sorted(attainment["co"].items())
        ]
        po_rows = [["PO", "Attainment %"]] + [
            [k, f"{v:.2f}"] for k, v in sorted(attainment["po"].items())
        ]
        story.append(Table(co_rows, colWidths=[4 * cm, 4 * cm]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Table(po_rows, colWidths=[4 * cm, 4 * cm]))

        doc.build(story)
        return buffer.getvalue()
