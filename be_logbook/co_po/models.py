from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class CO(models.Model):
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    program = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Course Outcome")
        verbose_name_plural = _("Course Outcomes")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class PO(models.Model):
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Program Outcome")
        verbose_name_plural = _("Program Outcomes")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class COPOAttainment(models.Model):
    """Snapshot of computed attainment for a review/group.

    NOTE: The calculation method is centralized in COPOService. The official
    BE marking Excel workbook was not available in this repository at build
    time, so the implemented method is a transparent, documented default
    (weighted average of normalized criterion attainment). It is explicitly
    NOT claimed to be the official formula and must be replaced once the
    official workbook is supplied. See COPOService.ATTAINMENT_METHOD.
    """

    group = models.ForeignKey(
        "groups.ProjectGroup", on_delete=models.CASCADE, related_name="copo"
    )
    review = models.ForeignKey(
        "reviews.Review",
        on_delete=models.CASCADE,
        related_name="copo",
        null=True,
        blank=True,
    )
    co_code = models.CharField(max_length=20, blank=True)
    po_code = models.CharField(max_length=20, blank=True)
    attainment = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    method = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("CO/PO Attainment")
        verbose_name_plural = _("CO/PO Attainments")
        ordering = ["group", "co_code", "po_code"]

    def __str__(self) -> str:
        return f"{self.co_code or self.po_code} = {self.attainment}"
