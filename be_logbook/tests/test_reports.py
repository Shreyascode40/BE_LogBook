from __future__ import annotations

import pytest
from django.utils import timezone

from be_logbook.audit.models import AuditLog
from be_logbook.groups.models import ProjectGroup
from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.reviews.services import ReviewService
from be_logbook.reports.services import ReportService


@pytest.mark.django_db
def test_overview_requires_hod(env, auth):
    student = auth(env["students"][0])
    resp = student.get("/api/v1/reports/overview/")
    assert resp.status_code in (403, 401)


@pytest.mark.django_db
def test_overview_counts(env, auth):
    hod = auth(env["hod"])
    resp = hod.get("/api/v1/reports/overview/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_groups"] >= 1
    assert "completed_groups" in data
    assert "overdue_groups" in data


@pytest.mark.django_db
def test_overdue_and_workload_endpoints(env, auth):
    hod = auth(env["hod"])
    assert hod.get("/api/v1/reports/overdue/").status_code == 200
    assert hod.get("/api/v1/reports/faculty_workload/").status_code == 200
    assert hod.get("/api/v1/reports/reviewer_workload/").status_code == 200
    progress = hod.get("/api/v1/reports/group_progress/").json()
    assert isinstance(progress, list)
    assert progress[0]["group_number"] == env["group"].group_number


@pytest.mark.django_db
def test_export_csv(env, auth):
    hod = auth(env["hod"])
    resp = hod.get("/api/v1/reports/export/")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")


@pytest.mark.django_db
def test_report_service_direct(env):
    ov = ReportService.overview()
    assert ov["total_groups"] >= 1
    gp = ReportService.group_progress()
    assert any(g["group_number"] == env["group"].group_number for g in gp)
