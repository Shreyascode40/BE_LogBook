from __future__ import annotations

import pytest

from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewMarkCorrection


@pytest.mark.django_db
def test_mark_entry_validation(env, auth):
    reviewer = auth(env["reviewer"])
    assignment = env["group"].review_assignments.get(
        stage=env["stages"]["REVIEW_1"], is_active=True
    )
    resp = reviewer.post(
        "/api/v1/reviews/",
        {
            "assignment_id": assignment.id,
            "rubric_id": env["rubric"].id,
            "review_type": "INTERNAL",
            "date": "2025-09-01",
        },
    )
    assert resp.status_code == 201
    review_id = resp.json()["id"]
    c1 = env["rubric"].criteria.get(code="C1")
    c2 = env["rubric"].criteria.get(code="C2")

    # Negative marks rejected
    resp = reviewer.post(
        f"/api/v1/reviews/{review_id}/enter_mark/",
        {"criterion_id": c1.id, "obtained": -1},
    )
    assert resp.status_code == 422

    # Exceeds max rejected
    resp = reviewer.post(
        f"/api/v1/reviews/{review_id}/enter_mark/",
        {"criterion_id": c1.id, "obtained": 99},
    )
    assert resp.status_code == 422

    # Valid marks
    resp = reviewer.post(
        f"/api/v1/reviews/{review_id}/enter_mark/",
        {"criterion_id": c1.id, "obtained": 8},
    )
    assert resp.status_code == 200
    resp = reviewer.post(
        f"/api/v1/reviews/{review_id}/enter_mark/",
        {"criterion_id": c2.id, "obtained": 7},
    )
    assert resp.status_code == 200

    # Cannot finalize without all required? Both required entered -> fine
    resp = reviewer.post(f"/api/v1/reviews/{review_id}/finalize/")
    assert resp.status_code == 200
    review = Review.objects.get(id=review_id)
    assert review.status == "FINALIZED"
    assert review.total_obtained == 15
    assert review.total_max == 20


@pytest.mark.django_db
def test_mark_correction_audit(env, auth):
    reviewer = auth(env["reviewer"])
    hod = auth(env["hod"])
    assignment = env["group"].review_assignments.get(
        stage=env["stages"]["REVIEW_1"], is_active=True
    )
    resp = reviewer.post(
        "/api/v1/reviews/",
        {
            "assignment_id": assignment.id,
            "rubric_id": env["rubric"].id,
            "review_type": "INTERNAL",
            "date": "2025-09-01",
        },
    )
    review_id = resp.json()["id"]
    c1 = env["rubric"].criteria.get(code="C1")
    reviewer.post(
        f"/api/v1/reviews/{review_id}/enter_mark/",
        {"criterion_id": c1.id, "obtained": 8},
    )
    reviewer.post(
        f"/api/v1/reviews/{review_id}/enter_mark/",
        {"criterion_id": env["rubric"].criteria.get(code="C2").id, "obtained": 7},
    )
    reviewer.post(f"/api/v1/reviews/{review_id}/finalize/")

    # HOD requests correction
    resp = hod.post(
        f"/api/v1/reviews/{review_id}/request_correction/", {"reason": "audit"}
    )
    assert resp.status_code == 200
    assert Review.objects.get(id=review_id).status == "CORRECTION_REQUESTED"

    # HOD corrects mark
    resp = hod.post(
        f"/api/v1/reviews/{review_id}/correct_mark/",
        {"criterion_id": c1.id, "new_obtained": 10, "reason": "review"},
    )
    assert resp.status_code == 200
    assert Review.objects.get(id=review_id).status == "CORRECTED"
    assert ReviewMarkCorrection.objects.filter(review_id=review_id).exists()


@pytest.mark.django_db
def test_student_cannot_finalize_review(env, auth):
    student = auth(env["students"][0])
    assignment = env["group"].review_assignments.get(
        stage=env["stages"]["REVIEW_1"], is_active=True
    )
    # student cannot even create the review (not the assigned reviewer)
    resp = student.post(
        "/api/v1/reviews/",
        {
            "assignment_id": assignment.id,
            "rubric_id": env["rubric"].id,
            "review_type": "INTERNAL",
            "date": "2025-09-01",
        },
    )
    assert resp.status_code in (403, 422)
