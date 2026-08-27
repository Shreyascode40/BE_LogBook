from __future__ import annotations

import pytest

from be_logbook.audit.models import AuditLog


@pytest.mark.django_db
def test_group_creation_creates_audit(env, auth):
    hod = auth(env["hod"])
    before = AuditLog.objects.count()
    resp = hod.post(
        "/api/v1/groups/create_group/",
        {
            "group_number": "GNEW",
            "academic_year_id": env["ay"].id,
            "department_id": env["dept"].id,
        },
    )
    assert resp.status_code == 201
    assert AuditLog.objects.count() == before + 1
    log = AuditLog.objects.latest("timestamp")
    assert log.action == "GROUP_CREATED"
    assert log.actor == env["hod"]


@pytest.mark.django_db
def test_audit_is_append_only_via_api(env, auth):
    hod = auth(env["hod"])
    resp = hod.get("/api/v1/audit/")
    assert resp.status_code == 200
    # Non-HOD cannot access
    student = auth(env["students"][0])
    resp = student.get("/api/v1/audit/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_submission_approve_audited(env, auth):
    stage = env["stages"]["PROJECT_INFO"]
    section = env["sections"]["PROJECT_INFO"]
    student = auth(env["students"][0])
    guide = auth(env["guide"])
    resp = student.post(
        "/api/v1/submissions/",
        {
            "group_id": env["group"].id,
            "stage_id": stage.id,
            "section_id": section.id,
            "data": {},
        },
    )
    assert resp.status_code == 201
    sub_id = resp.json()["id"]
    student.post(f"/api/v1/submissions/{sub_id}/submit/")
    guide.post(f"/api/v1/submissions/{sub_id}/begin_review/")
    before = AuditLog.objects.count()
    guide.post(f"/api/v1/submissions/{sub_id}/approve/")
    assert AuditLog.objects.count() > before
    assert AuditLog.objects.filter(action="SUBMISSION_APPROVED").exists()


@pytest.mark.django_db
def test_document_upload_audited(env, auth):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from be_logbook.documents.models import Document

    student = auth(env["students"][0])
    f = SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf")
    before = AuditLog.objects.count()
    resp = student.post(
        "/api/v1/documents/",
        {"file": f, "document_type": "REPORT", "group_id": env["group"].id},
        format="multipart",
    )
    assert resp.status_code == 201
    assert AuditLog.objects.count() == before + 1
    assert AuditLog.objects.filter(action="DOCUMENT_UPLOADED").exists()


@pytest.mark.django_db
def test_review_finalize_audited(env, auth):
    from be_logbook.reviews.models import Review
    from be_logbook.reviews.models import ReviewAssignment
    from be_logbook.reviews.services import ReviewService

    reviewer = env["reviewer"]
    ra = ReviewAssignment.objects.get(
        group=env["group"], stage=env["stages"]["REVIEW_1"], is_active=True
    )
    review = Review.objects.create(
        assignment=ra,
        group=env["group"],
        reviewer=reviewer,
        stage=env["stages"]["REVIEW_1"],
        rubric=env["rubric"],
        date="2025-09-10",
    )
    for crit in env["rubric"].criteria.all():
        ReviewService.enter_mark(review, crit, crit.max_marks, "", reviewer)
    before = AuditLog.objects.count()
    ReviewService.finalize(review, reviewer)
    assert AuditLog.objects.count() > before
    assert AuditLog.objects.filter(action="REVIEW_FINALIZED").exists()
