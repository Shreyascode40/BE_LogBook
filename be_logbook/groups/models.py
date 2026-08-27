from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.users.models import User


class GroupStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not Started"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    CHANGES_REQUIRED = "CHANGES_REQUIRED", "Changes Required"
    APPROVED = "APPROVED", "Approved"
    LOCKED = "LOCKED", "Locked"
    OVERDUE = "OVERDUE", "Overdue"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ProjectGroup(models.Model):
    group_number = models.CharField(max_length=30)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="groups"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="groups"
    )
    status = models.CharField(
        max_length=20, choices=GroupStatus.choices, default=GroupStatus.NOT_STARTED
    )
    current_stage = models.ForeignKey(
        "workflow.Stage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Project Group")
        verbose_name_plural = _("Project Groups")
        ordering = ["academic_year", "group_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "group_number"],
                name="uniq_group_number_per_academic_year",
            )
        ]

    def __str__(self) -> str:
        return f"Group {self.group_number} ({self.academic_year.name})"

    @property
    def active_guide(self):
        from .models import GuideAssignment

        ga = (
            GuideAssignment.objects.filter(group=self, is_active=True)
            .select_related("faculty")
            .first()
        )
        return ga.faculty if ga else None


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    LEFT = "LEFT", "Left"
    REMOVED = "REMOVED", "Removed"


class GroupMembership(models.Model):
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.CASCADE, related_name="memberships"
    )
    student = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="group_memberships"
    )
    status = models.CharField(
        max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE
    )
    designation = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("e.g. Team Lead, Member"),
    )
    join_date = models.DateField(auto_now_add=True)
    leave_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Group Membership")
        verbose_name_plural = _("Group Memberships")
        ordering = ["group", "join_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "student"],
                condition=models.Q(status="ACTIVE"),
                name="uniq_active_membership_per_group",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student} in {self.group}"


class GuideAssignment(models.Model):
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.CASCADE, related_name="guide_assignments"
    )
    faculty = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="guide_assignments"
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="guide_assigned_by"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    end_date = models.DateField(null=True, blank=True)
    reason = models.TextField(
        blank=True, help_text=_("Reason for (re)assignment / reassignment")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Guide Assignment")
        verbose_name_plural = _("Guide Assignments")
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["group"],
                condition=models.Q(is_active=True),
                name="uniq_active_guide_per_group",
            )
        ]

    def __str__(self) -> str:
        return f"{self.faculty} -> {self.group}"
