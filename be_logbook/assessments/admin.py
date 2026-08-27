from __future__ import annotations

from django.contrib import admin

from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ["name", "academic_year", "is_active"]


@admin.register(RubricCriterion)
class RubricCriterionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "rubric", "max_marks", "co_code", "po_code"]
    list_filter = ["rubric"]
