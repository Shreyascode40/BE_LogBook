from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from be_logbook.academics.models import Term
from be_logbook.users.models import User
from be_logbook.workflow.models import Stage


class Project(models.Model):
    group = models.OneToOneField(
        "groups.ProjectGroup", on_delete=models.CASCADE, related_name="project"
    )
    title = models.CharField(max_length=300)
    area = models.CharField(max_length=150, blank=True, help_text=_("Domain / area"))
    description = models.TextField(blank=True)
    guide = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guided_projects",
        help_text=_("Active guide (kept in sync with GuideAssignment)."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self) -> str:
        return self.title

    def sync_guide(self) -> None:
        guide = self.group.active_guide
        if self.guide_id != (guide.id if guide else None):
            self.guide = guide
            self.save(update_fields=["guide", "updated_at"])


class ProjectSchedule(models.Model):
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="schedule"
    )
    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    milestones = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Schedule for {self.project}"


class TopicFinalization(models.Model):
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="topic_finalization"
    )
    finalized_topic = models.TextField(blank=True)
    finalized_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Topic finalization for {self.project}"


class CompetitionDetail(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="competitions"
    )
    name = models.CharField(max_length=200)
    date = models.DateField(null=True, blank=True)
    prize = models.CharField(max_length=100, blank=True)
    certificate = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competitions",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Competition: {self.name}"


class PublicationDetail(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="publications"
    )
    title = models.CharField(max_length=300)
    venue = models.CharField(max_length=200, blank=True)
    date = models.DateField(null=True, blank=True)
    link = models.URLField(blank=True)
    certificate = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publications",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Publication: {self.title}"


class TermRecord(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="term_records"
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="term_records"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Term Record")
        verbose_name_plural = _("Term Records")
        unique_together = [("project", "term")]

    def __str__(self) -> str:
        return f"{self.term} record for {self.project}"


class FinalSubmissionInfo(models.Model):
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="final_submission"
    )
    submitted = models.BooleanField(default=False)
    submitted_date = models.DateField(null=True, blank=True)
    certificate = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="final_submissions",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Final submission for {self.project}"
