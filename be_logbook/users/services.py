from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from be_logbook.utils.exceptions import BusinessRuleViolation

if TYPE_CHECKING:
    from be_logbook.academics.models import AcademicYear
    from be_logbook.academics.models import Department
    from be_logbook.users.models import User


class UserService:
    """HOD-driven account management. All actions are audited."""

    @classmethod
    @transaction.atomic
    def create_student(
        cls,
        *,
        email,
        name,
        password,
        roll_number,
        department,
        academic_year=None,
        phone="",
        created_by=None,
        request=None,
    ):
        from be_logbook.users.models import StudentProfile
        from be_logbook.users.models import User

        if User.objects.filter(email__iexact=email).exists():
            msg = "A user with this email already exists."
            raise BusinessRuleViolation({"email": [msg]})
        if StudentProfile.objects.filter(roll_number=roll_number).exists():
            msg = "This roll number is already registered."
            raise BusinessRuleViolation({"roll_number": [msg]})
        user = User.objects.create_user(
            email=email, name=name, password=password, role="STUDENT", is_active=True
        )
        StudentProfile.objects.create(
            user=user,
            roll_number=roll_number,
            department=department,
            academic_year=academic_year,
            phone=phone,
        )
        cls._audit(
            user, created_by, "USER_CREATED", new_state="STUDENT", request=request
        )
        return user

    @classmethod
    @transaction.atomic
    def create_faculty(
        cls,
        *,
        email,
        name,
        password,
        employee_id,
        department,
        designation="",
        phone="",
        created_by=None,
        request=None,
    ):
        from be_logbook.users.models import FacultyProfile
        from be_logbook.users.models import User

        if User.objects.filter(email__iexact=email).exists():
            msg = "A user with this email already exists."
            raise BusinessRuleViolation({"email": [msg]})
        if FacultyProfile.objects.filter(employee_id=employee_id).exists():
            msg = "This employee id is already registered."
            raise BusinessRuleViolation({"employee_id": [msg]})
        user = User.objects.create_user(
            email=email, name=name, password=password, role="FACULTY", is_active=True
        )
        FacultyProfile.objects.create(
            user=user,
            employee_id=employee_id,
            department=department,
            designation=designation,
            phone=phone,
        )
        cls._audit(
            user, created_by, "USER_CREATED", new_state="FACULTY", request=request
        )
        return user

    @classmethod
    @transaction.atomic
    def set_active(cls, user, active: bool, actor=None, request=None):
        user.is_active = active
        user.save(update_fields=["is_active", "updated_at"])
        action = "USER_ACTIVATED" if active else "USER_DEACTIVATED"
        cls._audit(user, actor, action, new_state=str(active), request=request)
        return user

    @classmethod
    def _audit(cls, user, actor, action, new_state=None, request=None):
        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=actor,
            action=action,
            entity="User",
            object_id=user.id,
            new_state=new_state,
            request=request,
        )
