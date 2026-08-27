from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.users.models import User
from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage


class SubmissionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    CHANGES_REQUIRED = "CHANGES_REQUIRED", "Changes Required"
    RESUBMITTED = "RESUBMITTED", "Resubmitted"
    APPROVED = "APPROVED", "Approved"
    LOCKED = "LOCKED", "Locked"
    OVERDUE = "OVERDUE", "Overdue"
    CANCELLED = "CANCELLED", "Cancelled"


class Submission(models.Model):
    """A logical submission for a (group, stage, section). Versions are kept."""

    group = models.ForeignKey(
        "groups.ProjectGroup", on_delete=models.CASCADE, related_name="submissions"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="submissions",
        null=True,
        blank=True,
    )
    stage = models.ForeignKey(
        Stage, on_delete=models.PROTECT, related_name="submissions"
    )
    section = models.ForeignKey(
        Section, on_delete=models.PROTECT, related_name="submissions"
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="submissions_made"
    )
    status = models.CharField(
        max_length=20, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT
    )
    version_number = models.PositiveIntegerField(default=1)
    data = models.JSONField(default=dict, blank=True)
    current_approved_version = models.PositiveIntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Submission")
        verbose_name_plural = _("Submissions")
        ordering = ["group", "stage", "section"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "stage", "section"],
                name="uniq_submission_per_group_stage_section",
            )
        ]

    def __str__(self) -> str:
        return f"Submission {self.group} / {self.stage} / {self.section} v{self.version_number}"


class SubmissionVersion(models.Model):
    """Immutable snapshot of a submission at a given version/state."""

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=SubmissionStatus.choices)
    submitted_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="submission_versions"
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Submission Version")
        verbose_name_plural = _("Submission Versions")
        ordering = ["submission", "version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "version_number"],
                name="uniq_submission_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.submission} v{self.version_number} ({self.status})"


class FacultyRemark(models.Model):
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="remarks"
    )
    author = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="faculty_remarks"
    )
    role = models.CharField(max_length=20, blank=True)
    text = models.TextField()
    version = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_remarks_link",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Faculty Remark")
        verbose_name_plural = _("Faculty Remarks")
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Remark by {self.author} on {self.submission}"


class Approval(models.Model):
    DECISION = (
        ("APPROVED", "Approved"),
        ("CHANGES_REQUIRED", "Changes Required"),
        ("REJECTED", "Rejected"),
    )
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="approvals"
    )
    approver = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="approvals_made"
    )
    role = models.CharField(max_length=20, blank=True)
    decision = models.CharField(max_length=20, choices=DECISION)
    remarks = models.TextField(blank=True)
    version = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approvals",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Approval")
        verbose_name_plural = _("Approvals")
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.decision} by {self.approver} on {self.submission}"


class ChangeRequest(models.Model):
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="change_requests"
    )
    requested_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="change_requests_made"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Change Request")
        verbose_name_plural = _("Change Requests")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Change request on {self.submission}"


class StudentActivity(models.Model):
    ACTIVITY_STATUS = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )
    group = models.ForeignKey(
        "groups.ProjectGroup", on_delete=models.CASCADE, related_name="activities"
    )
    student = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="activities"
    )
    stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    date = models.DateField()
    description = models.TextField()
    work_performed = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ACTIVITY_STATUS, default="DRAFT")
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    faculty_remarks = models.TextField(blank=True)
    approval = models.ForeignKey(
        Approval,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Student Activity")
        verbose_name_plural = _("Student Activities")
        ordering = ["date"]

    def __str__(self) -> str:
        return f"Activity {self.date} by {self.student}"
