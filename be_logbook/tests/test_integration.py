from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from be_logbook.assessments.models import RubricCriterion
from be_logbook.documents.models import Document
from be_logbook.documents.services import DocumentService
from be_logbook.groups.services import GroupService
from be_logbook.logbook.models import GeneratedLogBook
from be_logbook.logbook.services import LogBookGenerationService
from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.reviews.services import ReviewService
from be_logbook.submissions.models import Submission
from be_logbook.submissions.services import SubmissionService
from be_logbook.workflow.models import Stage


def _complete_stage(env, stage, request=None):
    section = env["sections"][stage.code]
    group = env["group"]
    # Student submission
    submission, _ = Submission.objects.get_or_create(
        group=group,
        stage=stage,
        section=section,
        defaults={"submitted_by": env["students"][0], "data": {"x": 1}},
    )
    if submission.status in ("DRAFT", "CHANGES_REQUIRED", "RESUBMITTED"):
        submission.data = {"x": 1}
        submission.save()
        SubmissionService.submit(submission, env["students"][0], request=request)
    if submission.status == "SUBMITTED":
        SubmissionService.begin_review(submission, env["guide"], request=request)
    if submission.status == "UNDER_REVIEW":
        SubmissionService.approve(submission, env["guide"], request=request)
    # Reviews
    if stage.reviewer_approval_required:
        assignment = ReviewAssignment.objects.filter(
            group=group, stage=stage, is_active=True
        ).first()
        if not assignment:
            GroupService.assign_reviewer(
                group=group,
                reviewer=env["reviewer"],
                stage=stage,
                assigned_by=env["hod"],
                request=request,
            )
            assignment = ReviewAssignment.objects.filter(
                group=group, stage=stage, is_active=True
            ).first()
        review = Review.objects.filter(assignment=assignment).first()
        if not review:
            review = Review.objects.create(
                assignment=assignment,
                group=group,
                reviewer=env["reviewer"],
                stage=stage,
                rubric=env["rubric"],
                date="2025-09-01",
            )
        for crit in env["rubric"].criteria.all():
            ReviewService.enter_mark(review, crit, crit.max_marks, "", env["reviewer"])
        if review.status != "FINALIZED":
            ReviewService.finalize(review, env["reviewer"], request=request)


@pytest.mark.django_db
def test_full_integration_flow(env):
    # 1. Logbook generation must fail before completion.
    ok, missing = LogBookGenerationService.validate(env["project"])
    assert not ok

    # 2. Complete every stage in order.
    for stage in Stage.objects.filter(is_active=True).order_by("display_order"):
        _complete_stage(env, stage)

    # 3. Upload required REPORT document.
    f = SimpleUploadedFile(
        "report.pdf", b"%PDF-1.4 report", content_type="application/pdf"
    )
    DocumentService.upload(
        document_type="REPORT",
        file_obj=f,
        user=env["students"][0],
        group=env["group"],
        project=env["project"],
    )

    # 4. CO/PO computed.
    from be_logbook.co_po.services import COPOService

    attainment = COPOService.compute_for_group(env["group"])
    assert isinstance(attainment, dict)

    # 5. Group should be completed.
    env["group"].refresh_from_db()
    assert env["group"].status == "COMPLETED"

    # 6. Generate logbook.
    gen = LogBookGenerationService.generate(env["project"], env["hod"])
    assert isinstance(gen, GeneratedLogBook)
    assert gen.file
    assert gen.status == "READY"

    # 7. Regeneration bumps version.
    gen2 = LogBookGenerationService.generate(env["project"], env["hod"])
    assert gen2.version == gen.version + 1
