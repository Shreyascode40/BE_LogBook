from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class StageApproverRole(models.TextChoices):
    GUIDE = "GUIDE", "Guide"
    REVIEWER = "REVIEWER", "Reviewer"
    BOTH = "BOTH", "Guide & Reviewer"


class Stage(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    guide_approval_required = models.BooleanField(default=True)
    reviewer_approval_required = models.BooleanField(default=False)
    document_required = models.BooleanField(default=False)
    marks_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stage")
        verbose_name_plural = _("Stages")
        ordering = ["display_order"]

    def __str__(self) -> str:
        return f"{self.display_order}. {self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if self.display_order is None:
            self.display_order = (Stage.objects.count() or 0) + 1
        super().save(*args, **kwargs)


class StageDependency(models.Model):
    stage = models.ForeignKey(
        Stage, on_delete=models.CASCADE, related_name="dependencies"
    )
    depends_on = models.ForeignKey(
        Stage, on_delete=models.CASCADE, related_name="dependents"
    )

    class Meta:
        verbose_name = _("Stage Dependency")
        verbose_name_plural = _("Stage Dependencies")
        unique_together = [("stage", "depends_on")]

    def __str__(self) -> str:
        return f"{self.stage.code} depends on {self.depends_on.code}"

    def save(self, *args, **kwargs):
        if self.stage_id and self.stage_id == self.depends_on_id:
            msg = "A stage cannot depend on itself."
            raise ValueError(msg)
        super().save(*args, **kwargs)


class StageDeadline(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="deadlines")
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.CASCADE,
        related_name="stage_deadlines",
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    submission_deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stage Deadline")
        verbose_name_plural = _("Stage Deadlines")
        unique_together = [("stage", "academic_year")]

    def __str__(self) -> str:
        return f"{self.stage.code} @ {self.academic_year.name}"


class SectionType(models.TextChoices):
    PROJECT_INFO = "PROJECT_INFO", "Project & Group Information"
    GROUP_INFO = "GROUP_INFO", "Group Information"
    STUDENT_INFO = "STUDENT_INFO", "Student Information"
    SCHEDULE = "SCHEDULE", "Project Schedule"
    TOPIC_FINALIZATION = "TOPIC_FINALIZATION", "Topic Finalization"
    MONTHLY_ACTIVITY = "MONTHLY_ACTIVITY", "Monthly Activity Charts"
    RTM = "RTM", "Requirement Traceability Matrix"
    COST_ESTIMATION = "COST_ESTIMATION", "Cost Estimation"
    UML_DESIGN = "UML_DESIGN", "UML / Design"
    REVIEWS = "REVIEWS", "Reviews"
    COMPETITION = "COMPETITION", "Competition Details"
    PUBLICATION = "PUBLICATION", "Paper Publication Details"
    TERM_I = "TERM_I", "Term-I"
    TERM_II = "TERM_II", "Term-II"
    FINAL_SUBMISSION = "FINAL_SUBMISSION", "Final Submission"
    OTHER = "OTHER", "Other"


class Section(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=30, choices=SectionType.choices)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Section")
        verbose_name_plural = _("Sections")
        ordering = ["stage", "display_order"]

    def __str__(self) -> str:
        return f"{self.name} [{self.section_type}]"
