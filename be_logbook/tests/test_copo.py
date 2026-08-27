from __future__ import annotations

import pytest

from be_logbook.co_po.models import COPOAttainment
from be_logbook.co_po.services import COPOService
from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.reviews.services import ReviewService


def _finalize_review(env, user):
    ra = ReviewAssignment.objects.get(
        group=env["group"], stage=env["stages"]["REVIEW_1"], is_active=True
    )
    review = Review.objects.create(
        assignment=ra,
        group=env["group"],
        reviewer=user,
        stage=env["stages"]["REVIEW_1"],
        rubric=env["rubric"],
        date="2025-09-10",
    )
    criteria = list(env["rubric"].criteria.all())
    ReviewService.enter_mark(review, criteria[0], 8, "ok", user)
    ReviewService.enter_mark(review, criteria[1], 6, "ok", user)
    ReviewService.finalize(review, user)
    return review


@pytest.mark.django_db
def test_compute_for_group_aggregates_co_po(env, auth):
    _finalize_review(env, env["reviewer"])
    data = COPOService.compute_for_group(env["group"])
    # Both criteria map to distinct CO/PO codes via the seeded rubric.
    assert "CO1" in data["co"]
    assert "CO2" in data["co"]
    assert "PO1" in data["po"]
    assert "PO2" in data["po"]
    assert data["co"]["CO1"] > 0


@pytest.mark.django_db
def test_snapshot_persists_attainment(env, auth):
    _finalize_review(env, env["reviewer"])
    snaps = COPOService.snapshot_for_group(env["group"])
    assert len(snaps) >= 4
    assert COPOAttainment.objects.filter(group=env["group"]).exists()


@pytest.mark.django_db
def test_group_copo_endpoint(env, auth):
    reviewer = auth(env["reviewer"])
    _finalize_review(env, env["reviewer"])
    client = auth(env["reviewer"])
    resp = client.get(f"/api/v1/co-po/group/{env['group'].id}/")
    assert resp.status_code == 200
    assert "CO1" in resp.json()["data"]["co"]
