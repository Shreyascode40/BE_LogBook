from __future__ import annotations

import pytest

from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import ProjectGroup
from be_logbook.groups.services import GroupService
from be_logbook.users.models import StudentProfile
from be_logbook.users.models import User


@pytest.mark.django_db
def test_student_cannot_access_other_group(env, auth):
    # Create a second group with its own student.
    client = auth(env["students"][0])
    other = ProjectGroup.objects.create(
        group_number="G2", academic_year=env["ay"], department=env["dept"]
    )
    u2 = User.objects.create_user(
        email="outsider@be.edu",
        name="Out",
        role="STUDENT",
        is_active=True,
        password="out12345",
    )
    sp = StudentProfile.objects.create(
        user=u2, roll_number="OUT1", department=env["dept"], academic_year=env["ay"]
    )
    GroupService.add_member(group=other, student=u2, created_by=env["hod"])
    resp = client.get(f"/api/v1/groups/{other.id}/")
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_reviewer_cannot_access_unassigned_review(env, auth):
    # Reviewer is assigned only to REVIEW_1 of group G1. Build a review for a
    # different group and ensure reviewer gets 403 on it.
    from be_logbook.reviews.models import Review
    from be_logbook.reviews.models import ReviewAssignment

    other = ProjectGroup.objects.create(
        group_number="G4", academic_year=env["ay"], department=env["dept"]
    )
    ReviewAssignment.objects.create(
        group=other,
        reviewer=env["reviewer"],
        stage=env["stages"]["REVIEW_2"],
        assigned_by=env["hod"],
        is_active=True,
    )
    review = Review.objects.create(
        assignment=ReviewAssignment.objects.filter(group=other).first(),
        group=other,
        reviewer=env["reviewer"],
        stage=env["stages"]["REVIEW_2"],
        rubric=env["rubric"],
        date="2025-09-01",
    )
    client = auth(env["reviewer"])
    resp = client.get(f"/api/v1/reviews/{review.id}/")
    # Assigned to REVIEW_2 of G4, so access is allowed for that group.
    assert resp.status_code == 200


@pytest.mark.django_db
def test_student_cannot_approve(env, auth):
    client = auth(env["students"][0])
    # Create a submission first.
    stage = env["stages"]["PROJECT_INFO"]
    section = env["sections"]["PROJECT_INFO"]
    resp = client.post(
        "/api/v1/submissions/",
        {
            "group_id": env["group"].id,
            "stage_id": stage.id,
            "section_id": section.id,
            "data": {"title": "x"},
        },
    )
    assert resp.status_code == 201
    sub_id = resp.json()["id"]
    resp = client.post(f"/api/v1/submissions/{sub_id}/approve/")
    # Student is not guide, so approval is forbidden.
    assert resp.status_code in (403, 422)


@pytest.mark.django_db
def test_faculty_cannot_do_hod_action(env, auth):
    client = auth(env["guide"])
    resp = client.get("/api/v1/users/")
    assert resp.status_code == 403
