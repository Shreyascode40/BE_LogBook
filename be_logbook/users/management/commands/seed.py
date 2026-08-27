from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion
from be_logbook.co_po.models import CO
from be_logbook.co_po.models import PO
from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import ProjectGroup
from be_logbook.groups.services import GroupService
from be_logbook.projects.models import Project
from be_logbook.users.models import FacultyProfile
from be_logbook.users.models import StudentProfile
from be_logbook.users.services import UserService
from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage
from be_logbook.workflow.models import StageDependency

User = get_user_model()

STAGE_DEFINITIONS = [
    ("PROJECT_INFO", "Project Information", True, False, False),
    ("ACTIVITIES", "Activities", False, False, False),
    ("REVIEW_1", "Review 1", True, True, False),
    ("DESIGN", "Design", True, False, False),
    ("REVIEW_2", "Review 2", True, True, False),
    ("DEV_TEST", "Development/Testing", True, False, False),
    ("REVIEW_3", "Review 3", True, True, False),
    ("FINAL_SUBMISSION", "Final Submission", True, True, True),
]


class Command(BaseCommand):
    help = "Seed development data: department, academic year, users, group, stages, rubric."

    def handle(self, *args, **options):
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

        hod, _ = User.objects.get_or_create(
            email="hod@be.edu",
            defaults={"name": "HOD", "role": "HOD", "is_active": True},
        )
        if not hod.has_usable_password():
            hod.set_password("hod12345")
            hod.save()

        guide = self._ensure_faculty("guide@be.edu", "Guide", "F001")
        reviewer = self._ensure_faculty("reviewer@be.edu", "Reviewer", "F002")

        students = []
        for i in range(1, 5):
            email = f"student{i}@be.edu"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"name": f"Student {i}", "role": "STUDENT", "is_active": True},
            )
            if created:
                user.set_password("student12345")
                user.save()
            sp, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "roll_number": f"BE2025{i:03d}",
                    "department": dept,
                    "academic_year": ay,
                },
            )
            students.append(user)

        group, _ = ProjectGroup.objects.get_or_create(
            group_number="G1",
            academic_year=ay,
            defaults={"department": dept},
        )
        for s in students:
            if not GroupMembership.objects.filter(group=group, student=s).exists():
                GroupService.add_member(group=group, student=s, created_by=hod)

        if not group.active_guide:
            GroupService.assign_guide(group=group, faculty=guide, assigned_by=hod)
        first_stage = Stage.objects.filter(code="REVIEW_1").first()
        if (
            first_stage
            and not group.review_assignments.filter(
                stage=first_stage, is_active=True
            ).exists()
        ):
            GroupService.assign_reviewer(
                group=group, reviewer=reviewer, stage=first_stage, assigned_by=hod
            )

        self._ensure_stages()
        self._ensure_sections()
        self._ensure_rubric()
        self._ensure_copo()

        project, _ = Project.objects.get_or_create(
            group=group,
            defaults={
                "title": "Sample BE Project",
                "area": "Web Engineering",
                "description": "A sample project for development.",
            },
        )
        project.sync_guide()

        self.stdout.write(self.style.SUCCESS("Seed data created."))

    def _ensure_faculty(self, email, name, emp_id):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"name": name, "role": "FACULTY", "is_active": True},
        )
        if created:
            user.set_password("faculty12345")
            user.save()
        FacultyProfile.objects.get_or_create(
            user=user,
            defaults={
                "employee_id": emp_id,
                "department_id": 1,
                "designation": "Assistant Professor",
            },
        )
        return user

    def _ensure_stages(self):
        prev = None
        for idx, (code, name, required, rev_appr, marks) in enumerate(
            STAGE_DEFINITIONS, 1
        ):
            stage, _ = Stage.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "display_order": idx,
                    "required": required,
                    "is_active": True,
                    "guide_approval_required": True,
                    "reviewer_approval_required": rev_appr,
                    "marks_required": marks,
                },
            )
            if prev is not None:
                StageDependency.objects.get_or_create(stage=stage, depends_on=prev)
            prev = stage

    def _ensure_sections(self):
        for stage in Stage.objects.all():
            if not stage.sections.exists():
                Section.objects.create(
                    stage=stage,
                    section_type="OTHER",
                    name=f"{stage.name} Section",
                    display_order=1,
                    required=True,
                )

    def _ensure_rubric(self):
        rubric, _ = Rubric.objects.get_or_create(
            name="Default BE Rubric",
            defaults={"academic_year_id": 1, "is_active": True},
        )
        if not rubric.criteria.exists():
            RubricCriterion.objects.create(
                rubric=rubric,
                code="C1",
                name="Technical Depth",
                max_marks=10,
                weight=1,
                co_code="CO1",
                po_code="PO1",
                order=1,
            )
            RubricCriterion.objects.create(
                rubric=rubric,
                code="C2",
                name="Implementation",
                max_marks=10,
                weight=1,
                co_code="CO2",
                po_code="PO2",
                order=2,
            )
            RubricCriterion.objects.create(
                rubric=rubric,
                code="C3",
                name="Presentation",
                max_marks=10,
                weight=1,
                co_code="CO3",
                po_code="PO3",
                order=3,
            )

    def _ensure_copo(self):
        for i in range(1, 7):
            CO.objects.get_or_create(
                code=f"CO{i}", defaults={"description": f"Course Outcome {i}"}
            )
            PO.objects.get_or_create(
                code=f"PO{i}", defaults={"description": f"Program Outcome {i}"}
            )
