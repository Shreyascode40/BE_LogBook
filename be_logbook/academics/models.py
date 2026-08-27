from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AcademicYear(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True,
        help_text=_("e.g. 2025-26"),
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Academic Year")
        verbose_name_plural = _("Academic Years")
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Only one active academic year at a time.
        if self.is_active:
            type(self).objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)


class Term(models.Model):
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="terms"
    )
    name = models.CharField(max_length=30, help_text=_("e.g. Term-I, Term-II"))
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Term")
        verbose_name_plural = _("Terms")
        ordering = ["academic_year", "start_date"]
        unique_together = [("academic_year", "name")]

    def __str__(self) -> str:
        return f"{self.academic_year.name} - {self.name}"
