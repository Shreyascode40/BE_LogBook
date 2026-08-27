from __future__ import annotations

import pytest

from be_logbook.submissions.models import Submission
from be_logbook.workflow.services import WorkflowService


@pytest.mark.django_db
def test_full_submission_flow(env, auth):
    stage = env["stages"]["PROJECT_INFO"]
    section = env["sections"]["PROJECT_INFO"]
    student = auth(env["students"][0])
    guide = auth(env["guide"])

    # Create draft
    resp = student.post(
        "/api/v1/submissions/",
        {
            "group_id": env["group"].id,
            "stage_id": stage.id,
            "section_id": section.id,
            "data": {"field": "value"},
        },
    )
    assert resp.status_code == 201
    sub_id = resp.json()["id"]
    assert resp.json()["status"] == "DRAFT"

    # Submit
    resp = student.post(f"/api/v1/submissions/{sub_id}/submit/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUBMITTED"

    # Guide begins review
    resp = guide.post(f"/api/v1/submissions/{sub_id}/begin_review/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "UNDER_REVIEW"

    # Guide requests changes
    resp = guide.post(
        f"/api/v1/submissions/{sub_id}/request_changes/", {"text": "fix this"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CHANGES_REQUIRED"

    # Student resubmits
    resp = student.post(f"/api/v1/submissions/{sub_id}/submit/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESUBMITTED"

    resp = guide.post(f"/api/v1/submissions/{sub_id}/begin_review/")
    assert resp.status_code == 200

    # Guide approves
    resp = guide.post(f"/api/v1/submissions/{sub_id}/approve/", {"remarks": "good"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # Next stage should now be unlocked
    assert WorkflowService.is_stage_unlocked(env["group"], env["stages"]["ACTIVITIES"])


@pytest.mark.django_db
def test_cannot_submit_locked_stage(env, auth):
    student = auth(env["students"][0])
    # REVIEW_1 is not unlocked initially (depends on ACTIVITIES <- PROJECT_INFO)
    resp = student.post(
        "/api/v1/submissions/",
        {
            "group_id": env["group"].id,
            "stage_id": env["stages"]["REVIEW_1"].id,
            "section_id": env["sections"]["REVIEW_1"].id,
            "data": {},
        },
    )
    assert resp.status_code in (401, 403, 422)
    assert Submission.objects.count() == 0


@pytest.mark.django_db
def test_approve_from_draft_invalid(env, auth):
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
    sub_id = resp.json()["id"]
    # Guide tries to approve a DRAFT -> invalid
    resp = guide.post(f"/api/v1/submissions/{sub_id}/approve/")
    assert resp.status_code == 422
