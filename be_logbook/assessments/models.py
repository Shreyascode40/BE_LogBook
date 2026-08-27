from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Rubric(models.Model):
    name = models.CharField(max_length=150)
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="rubrics",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Rubric")
        verbose_name_plural = _("Rubrics")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RubricCriterion(models.Model):
    rubric = models.ForeignKey(
        Rubric, on_delete=models.CASCADE, related_name="criteria"
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    max_marks = models.DecimalField(max_digits=8, decimal_places=2)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    co_code = models.CharField(max_length=20, blank=True, help_text=_("e.g. CO1"))
    po_code = models.CharField(max_length=20, blank=True, help_text=_("e.g. PO1"))
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Rubric Criterion")
        verbose_name_plural = _("Rubric Criteria")
        ordering = ["rubric", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["rubric", "code"], name="uniq_rubric_criterion_code"
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name} ({self.max_marks})"
