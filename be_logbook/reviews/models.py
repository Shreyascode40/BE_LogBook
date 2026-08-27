from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.users.models import User
from be_logbook.workflow.models import Stage


class ReviewAssignment(models.Model):
    group = models.ForeignKey(
        "groups.ProjectGroup",
        on_delete=models.CASCADE,
        related_name="review_assignments",
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="review_assignments"
    )
    stage = models.ForeignKey(
        Stage, on_delete=models.PROTECT, related_name="review_assignments"
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="review_assigned_by"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    end_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True, help_text=_("Reassignment reason if any"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Review Assignment")
        verbose_name_plural = _("Review Assignments")
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "stage"],
                condition=models.Q(is_active=True),
                name="uniq_active_reviewer_per_group_stage",
            )
        ]

    def __str__(self) -> str:
        return f"Review {self.reviewer} -> {self.group} / {self.stage}"


class ReviewStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    FINALIZED = "FINALIZED", "Finalized"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED", "Correction Requested"
    CORRECTED = "CORRECTED", "Corrected"


class Review(models.Model):
    assignment = models.ForeignKey(
        ReviewAssignment, on_delete=models.PROTECT, related_name="reviews"
    )
    group = models.ForeignKey(
        "groups.ProjectGroup", on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="reviews_conducted"
    )
    stage = models.ForeignKey(Stage, on_delete=models.PROTECT, related_name="reviews")
    rubric = models.ForeignKey(
        "assessments.Rubric", on_delete=models.PROTECT, related_name="reviews"
    )
    review_type = models.CharField(
        max_length=20,
        choices=[("INTERNAL", "Internal"), ("EXTERNAL", "External")],
        default="INTERNAL",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    total_max = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_obtained = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    remarks = models.TextField(blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"Review {self.id} - {self.group} / {self.stage}"


class ReviewMark(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="marks")
    criterion = models.ForeignKey(
        "assessments.RubricCriterion", on_delete=models.PROTECT, related_name="marks"
    )
    max_marks = models.DecimalField(max_digits=8, decimal_places=2)
    obtained_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Review Mark")
        verbose_name_plural = _("Review Marks")
        constraints = [
            models.UniqueConstraint(
                fields=["review", "criterion"], name="uniq_review_criterion_mark"
            )
        ]

    def __str__(self) -> str:
        return f"{self.criterion} = {self.obtained_marks}/{self.max_marks}"


class ReviewMarkCorrection(models.Model):
    """Append-only audit of an authorized mark correction."""

    review_mark = models.ForeignKey(
        ReviewMark, on_delete=models.PROTECT, related_name="corrections"
    )
    review = models.ForeignKey(
        Review, on_delete=models.PROTECT, related_name="mark_corrections"
    )
    corrected_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="mark_corrections_made"
    )
    old_obtained = models.DecimalField(max_digits=8, decimal_places=2)
    new_obtained = models.DecimalField(max_digits=8, decimal_places=2)
    reason = models.TextField()
    approval = models.ForeignKey(
        "submissions.Approval",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mark_corrections",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Review Mark Correction")
        verbose_name_plural = _("Review Mark Corrections")
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"Correction {self.old_obtained} -> {self.new_obtained}"
