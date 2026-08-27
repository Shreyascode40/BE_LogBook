from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

if TYPE_CHECKING:
    from be_logbook.users.models import User


def user_role(user: "User") -> str:
    return getattr(user, "role", "")


def is_hod(user: "User") -> bool:
    return bool(user and user.is_authenticated and user_role(user) == "HOD")


def is_faculty(user: "User") -> bool:
    return bool(user and user.is_authenticated and user_role(user) == "FACULTY")


def is_student(user: "User") -> bool:
    return bool(user and user.is_authenticated and user_role(user) == "STUDENT")


def is_reviewer_for(user: "User", group, stage=None) -> bool:
    """True if a faculty user has an active reviewer assignment for the group/stage."""
    if not is_faculty(user):
        return False
    from be_logbook.reviews.models import ReviewAssignment

    qs = ReviewAssignment.objects.filter(reviewer=user, group=group, is_active=True)
    if stage is not None:
        qs = qs.filter(stage=stage)
    return qs.exists()


def is_guide_for(user: "User", group) -> bool:
    if not is_faculty(user):
        return False
    from be_logbook.groups.models import GuideAssignment

    return GuideAssignment.objects.filter(
        faculty=user, group=group, is_active=True
    ).exists()


def is_group_member(user: "User", group) -> bool:
    if not is_student(user):
        return False
    from be_logbook.groups.models import GroupMembership

    return GroupMembership.objects.filter(
        student=user, group=group, status="ACTIVE"
    ).exists()


def can_access_group(user: "User", group) -> bool:
    """Object-level access to a project group.

    HOD -> any group in their department.
    Faculty -> active guide or active reviewer assignment.
    Student -> active membership.
    """
    if not user or not user.is_authenticated:
        return False
    if is_hod(user):
        return True
    if is_student(user):
        return is_group_member(user, group)
    if is_faculty(user):
        return is_guide_for(user, group) or is_reviewer_for(user, group)
    return False


def can_access_review(user: "User", review) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_hod(user):
        return True
    if is_faculty(user):
        return is_reviewer_for(user, review.group, review.stage)
    return False


def can_access_submission(user: "User", submission) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_hod(user):
        return True
    group = submission.group
    if is_student(user):
        return is_group_member(user, group)
    if is_faculty(user):
        return is_guide_for(user, group) or is_reviewer_for(
            user, group, submission.stage
        )
    return False


def can_access_document(user: "User", document) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_hod(user):
        return True
    group = document.group
    if group is None:
        return False
    if is_student(user):
        return is_group_member(user, group)
    if is_faculty(user):
        return is_guide_for(user, group) or is_reviewer_for(user, group)
    return False
