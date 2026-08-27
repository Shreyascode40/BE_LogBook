from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from be_logbook.utils.exceptions import BusinessRuleViolation

if TYPE_CHECKING:
    from be_logbook.academics.models import AcademicYear
    from be_logbook.academics.models import Department
    from be_logbook.groups.models import ProjectGroup
    from be_logbook.users.models import User
    from be_logbook.workflow.models import Stage


class GroupService:
    """HOD-controlled group, guide and reviewer assignment."""

    @classmethod
    @transaction.atomic
    def create_group(
        cls, *, group_number, academic_year, department, created_by=None, request=None
    ):
        from be_logbook.groups.models import ProjectGroup

        if ProjectGroup.objects.filter(
            group_number=group_number, academic_year=academic_year
        ).exists():
            msg = "Group number already exists in this academic year."
            raise BusinessRuleViolation({"group_number": [msg]})
        group = ProjectGroup.objects.create(
            group_number=group_number,
            academic_year=academic_year,
            department=department,
        )
        cls._audit(group, created_by, "GROUP_CREATED", request=request)
        return group

    @classmethod
    @transaction.atomic
    def add_member(
        cls, *, group, student, designation="", created_by=None, request=None
    ):
        from be_logbook.groups.models import GroupMembership

        if GroupMembership.objects.filter(student=student, status="ACTIVE").exists():
            msg = "Student already belongs to an active group."
            raise BusinessRuleViolation({"student": [msg]})
        if GroupMembership.objects.filter(group=group, student=student).exists():
            msg = "Student is already associated with this group."
            raise BusinessRuleViolation({"student": [msg]})
        membership = GroupMembership.objects.create(
            group=group, student=student, status="ACTIVE", designation=designation
        )
        cls._audit(
            group,
            created_by,
            "STUDENT_ADDED",
            new_state=str(student.id),
            request=request,
        )
        return membership

    @classmethod
    @transaction.atomic
    def remove_member(cls, *, group, student, created_by=None, request=None):
        from be_logbook.groups.models import GroupMembership

        membership = GroupMembership.objects.filter(
            group=group, student=student, status="ACTIVE"
        ).first()
        if not membership:
            msg = "Student is not an active member of this group."
            raise BusinessRuleViolation({"student": [msg]})
        from django.utils import timezone

        membership.status = "REMOVED"
        membership.leave_date = timezone.now().date()
        membership.save(update_fields=["status", "leave_date", "updated_at"])
        cls._audit(
            group,
            created_by,
            "STUDENT_REMOVED",
            new_state=str(student.id),
            request=request,
        )
        return membership

    @classmethod
    @transaction.atomic
    def assign_guide(cls, *, group, faculty, assigned_by, reason="", request=None):
        from be_logbook.groups.models import GuideAssignment

        # Deactivate any existing active guide.
        GuideAssignment.objects.filter(group=group, is_active=True).update(
            is_active=False, end_date=timezone.now().date()
        )
        assignment = GuideAssignment.objects.create(
            group=group,
            faculty=faculty,
            assigned_by=assigned_by,
            is_active=True,
            reason=reason,
        )
        # Sync project guide if project exists.
        if hasattr(group, "project") and group.project:
            group.project.sync_guide()
        cls._audit(
            group,
            assigned_by,
            "GUIDE_ASSIGNED",
            new_state=f"{faculty.id}",
            request=request,
        )
        return assignment

    @classmethod
    @transaction.atomic
    def assign_reviewer(
        cls, *, group, reviewer, stage, assigned_by, reason="", request=None
    ):
        from be_logbook.reviews.models import ReviewAssignment

        ReviewAssignment.objects.filter(
            group=group, stage=stage, is_active=True
        ).update(
            is_active=False,
            end_date=timezone.now().date(),
        )
        assignment = ReviewAssignment.objects.create(
            group=group,
            reviewer=reviewer,
            stage=stage,
            assigned_by=assigned_by,
            is_active=True,
            reason=reason,
        )
        cls._audit(
            group,
            assigned_by,
            "REVIEWER_ASSIGNED",
            new_state=f"{reviewer.id}:{stage.id}",
            request=request,
        )
        return assignment

    @classmethod
    def _audit(cls, group, actor, action, new_state=None, request=None):
        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=actor,
            action=action,
            entity="ProjectGroup",
            object_id=group.id,
            new_state=new_state,
            request=request,
        )
