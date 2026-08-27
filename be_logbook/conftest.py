from __future__ import annotations

import pytest
from django.utils import timezone

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion
from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import ProjectGroup
from be_logbook.groups.services import GroupService
from be_logbook.projects.models import Project
from be_logbook.users.models import FacultyProfile
from be_logbook.users.models import StudentProfile
from be_logbook.users.models import User
from be_logbook.users.services import UserService
from be_logbook.workflow.models import Stage
from be_logbook.workflow.models import StageDependency


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath
    settings.PRIVATE_MEDIA_ROOT = tmpdir.mkdir("private").strpath


def _build_stages():
    definitions = [
        ("PROJECT_INFO", "Project Information", True, False, False),
        ("ACTIVITIES", "Activities", False, False, False),
        ("REVIEW_1", "Review 1", True, True, False),
        ("DESIGN", "Design", True, False, False),
        ("REVIEW_2", "Review 2", True, True, False),
        ("DEV_TEST", "Development/Testing", True, False, False),
        ("REVIEW_3", "Review 3", True, True, False),
        ("FINAL_SUBMISSION", "Final Submission", True, True, True),
    ]
    prev = None
    stages = {}
    for idx, (code, name, required, rev, marks) in enumerate(definitions, 1):
        stage, _ = Stage.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "display_order": idx,
                "required": required,
                "is_active": True,
                "guide_approval_required": True,
                "reviewer_approval_required": rev,
                "marks_required": marks,
            },
        )
        if prev is not None:
            StageDependency.objects.get_or_create(stage=stage, depends_on=prev)
        stages[code] = stage
        prev = stage
    return stages


@pytest.fixture
def env(db):
    """Build a full departmental environment for tests."""
    dept, _ = Department.objects.get_or_create(
        code="COMP", defaults={"name": "Computer Engineering"}
    )
    ay, _ = AcademicYear.objects.get_or_create(
        name="2025-26",
        defaults={
            "start_date": "2025-08-01",
            "end_date": "2026-06-30",
            "is_active": True,
        },
    )

    hod = User.objects.create_user(
        email="hod@be.edu", name="HOD", role="HOD", is_active=True, password="hod12345"
    )
    guide = User.objects.create_user(
        email="guide@be.edu",
        name="Guide",
        role="FACULTY",
        is_active=True,
        password="fac12345",
    )
    reviewer = User.objects.create_user(
        email="reviewer@be.edu",
        name="Reviewer",
        role="FACULTY",
        is_active=True,
        password="fac12345",
    )
    FacultyProfile.objects.create(user=guide, employee_id="F001", department=dept)
    FacultyProfile.objects.create(user=reviewer, employee_id="F002", department=dept)

    students = []
    for i in range(1, 3):
        u = User.objects.create_user(
            email=f"student{i}@be.edu",
            name=f"Student {i}",
            role="STUDENT",
            is_active=True,
            password="stu12345",
        )
        StudentProfile.objects.create(
            user=u, roll_number=f"R{i}", department=dept, academic_year=ay
        )
        students.append(u)

    group = ProjectGroup.objects.create(
        group_number="G1", academic_year=ay, department=dept
    )
    for s in students:
        GroupService.add_member(group=group, student=s, created_by=hod)
    GroupService.assign_guide(group=group, faculty=guide, assigned_by=hod)
    stages = _build_stages()
    from be_logbook.workflow.models import Section

    sections = {}
    for stage in stages.values():
        section, _ = Section.objects.get_or_create(
            stage=stage,
            section_type="OTHER",
            defaults={
                "name": f"{stage.name} Section",
                "display_order": 1,
                "required": True,
            },
        )
        sections[stage.code] = section
    GroupService.assign_reviewer(
        group=group, reviewer=reviewer, stage=stages["REVIEW_1"], assigned_by=hod
    )

    project = Project.objects.create(
        group=group, title="Test Project", area="Web", description="desc"
    )
    project.sync_guide()

    rubric = Rubric.objects.create(name="Rubric", academic_year=ay, is_active=True)
    RubricCriterion.objects.create(
        rubric=rubric,
        code="C1",
        name="Tech",
        max_marks=10,
        weight=1,
        co_code="CO1",
        po_code="PO1",
        order=1,
        is_required=True,
    )
    RubricCriterion.objects.create(
        rubric=rubric,
        code="C2",
        name="Impl",
        max_marks=10,
        weight=1,
        co_code="CO2",
        po_code="PO2",
        order=2,
        is_required=True,
    )

    return {
        "dept": dept,
        "ay": ay,
        "hod": hod,
        "guide": guide,
        "reviewer": reviewer,
        "students": students,
        "group": group,
        "stages": stages,
        "sections": sections,
        "project": project,
        "rubric": rubric,
    }


@pytest.fixture
def api():
    from rest_framework.test import APIClient

    client = APIClient()
    client.default_format = "json"
    return client


@pytest.fixture
def auth():
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    def _auth(user):
        client = APIClient()
        client.default_format = "json"
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client

    return _auth
